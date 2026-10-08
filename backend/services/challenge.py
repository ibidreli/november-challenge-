"""One deterministic scorer for imports, webhooks and admin corrections."""
import os
from datetime import timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import load_only
from models.user import User
from models.activity import Activity
from models.challenge import ChallengeEdition, ChallengePeriod, DistanceTarget, ChallengeClaim
from services.time import local_today, utcnow, iso_utc
from services.schedule import CAPACITIES, active_month, initial_calendar, bounds, finale_date

def edition(db, lock=False):
    query = select(ChallengeEdition).where(ChallengeEdition.year == int(os.getenv("CHALLENGE_YEAR", "2026")),
                                           ChallengeEdition.month == active_month())
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    result = db.scalar(query)
    if not result:
        raise RuntimeError("Challenge edition has not been initialized")
    return result

def seed(db):
    year = int(os.getenv("CHALLENGE_YEAR", "2026"))
    month = active_month()
    spans, finale = initial_calendar(year, month)
    # The migration lock also protects initial edition creation on concurrent starts.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(2026100701)"))
    if db.scalar(select(ChallengeEdition).where(ChallengeEdition.year == year, ChallengeEdition.month == month)):
        return
    e = ChallengeEdition(year=year, month=month, finale_km=15, finale_on=finale)
    db.add(e)
    db.flush()
    for n, ((start, end), count) in enumerate(zip(spans, CAPACITIES), 1):
        db.add(ChallengePeriod(edition_id=e.id, number=n, starts_on=start,
            ends_on=end, draw_on=start - timedelta(days=1), capacity=count, draft_distances=[]))
    db.add(DistanceTarget(edition_id=e.id, km=15))
    db.commit()

def periods(db, e):
    return db.scalars(select(ChallengePeriod).where(ChallengePeriod.edition_id == e.id).order_by(ChallengePeriod.number)).all()

def configuration(db, admin=False):
    e = edition(db)
    today = local_today()
    ps = periods(db, e)
    first, last = min(p.starts_on for p in ps), finale_date(e)
    result = {"year": e.year, "month": e.month, "timezone": e.timezone, "finale_km": e.finale_km,
              "test_mode": e.month == 10, "starts_on": first.isoformat(),
              "finale_date": last.isoformat(), "server_date": today.isoformat(),
              "server_now": iso_utc(utcnow()), "periods": []}
    for p in ps:
        item = {"number": p.number, "starts_on": p.starts_on.isoformat(), "ends_on": p.ends_on.isoformat(),
                "draw_on": p.draw_on.isoformat(), "capacity": p.capacity,
                "published": bool(p.published_at), "current": p.starts_on <= today <= p.ends_on,
                "distances": sorted(p.draft_distances) if p.published_at else [],
                "editable": not p.published_at or today < p.starts_on}
        if admin:
            item["draft_distances"] = p.draft_distances
        result["periods"].append(item)
    return result

def lock_user(db, user_id, e=None):
    # Always edition -> user, including admin writes, to avoid lock inversion.
    e = e or edition(db, lock=True)
    user = db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))
    if not user:
        raise HTTPException(404, "Teilnehmer nicht gefunden.")
    return e, user

def rebuild_user(db, user_id, e=None):
    e, user = lock_user(db, user_id, e)
    ps = periods(db, e)
    targets = db.scalars(select(DistanceTarget).where(DistanceTarget.edition_id == e.id)).all()
    first, last = bounds(db, e)
    activities = db.scalars(select(Activity).where(Activity.user_id == user.id, Activity.date >= first,
        Activity.date <= min(last, local_today()), Activity.status.notin_(["deleted", "not_run", "admin_excluded"])).order_by(Activity.date, Activity.id)).all()
    db.query(ChallengeClaim).filter_by(user_id=user.id, edition_id=e.id).delete(synchronize_session="fetch")
    # Flush deletes before reusing unique (user, day/target) constraints.
    db.flush()
    days = {}
    for a in activities:
        a.effective_km = 0
        a.status = "daily_not_selected"
        days.setdefault(a.date, []).append(a)
    remaining = {t.id: t for t in targets}
    for day, runs in sorted(days.items()):
        # An explicit admin correction replaces Strava for that day.
        candidates = [a for a in runs if a.is_manual] or runs
        a = max(candidates, key=lambda run: (run.distance_km or 0, -(run.id or 0)))
        p = next((p for p in ps if p.starts_on <= day <= p.ends_on), None)
        if day == last:
            available = [t for t in remaining.values() if t.period_id is None]
        elif p and p.published_at:
            available = [t for t in remaining.values() if t.period_id == p.id]
        else:
            a.status = "waiting_draw"
            continue
        meters = Decimal(str(a.distance_km or 0)) * 1000
        suitable = [t for t in available if t.km * 1000 <= meters]
        if not suitable:
            a.status = "too_short" if available else "period_complete"
            continue
        target = max(suitable, key=lambda t: t.km)
        a.status, a.effective_km = "claimed", target.km
        remaining.pop(target.id)
        db.add(ChallengeClaim(user_id=user.id, edition_id=e.id, target_id=target.id,
                              activity_id=a.id, date=day, km=target.km))
    db.flush()
    return user

def rebuild_all(db, e):
    for uid in db.scalars(select(User.id).order_by(User.id)).all():
        rebuild_user(db, uid, e)

def participant(db, user, claims=None, targets=None, ps=None, personal=False, e=None):
    e = e or edition(db)
    claims = claims if claims is not None else db.scalars(select(ChallengeClaim).where(
        ChallengeClaim.edition_id == e.id, ChallengeClaim.user_id == user.id)).all()
    targets = targets if targets is not None else db.scalars(select(DistanceTarget).where(DistanceTarget.edition_id == e.id)).all()
    ps = ps if ps is not None else periods(db, e)
    by_km = {c.km: c for c in claims}
    by_target = {t.km: t for t in targets}
    by_period = {p.id: p for p in ps}
    today = local_today()
    cells = []
    for km in range(1, 31):
        claim, target = by_km.get(km), by_target.get(km)
        p = by_period.get(target.period_id) if target else None
        status = "completed" if claim else "upcoming"
        if not claim and target:
            start = p.starts_on if p else finale_date(e)
            end = p.ends_on if p else start
            status = "missed" if today > end else "open" if today >= start else "scheduled"
        cells.append({"km": km, "status": status, "period": p.number if p else None,
                      "finale": km == e.finale_km, "finale_date": finale_date(e).isoformat() if km == e.finale_km else None,
                      "completed_on": claim.date.isoformat() if claim else None})
    result = {"id": user.id, "name": user.name or "Läufer/in", "total_score": sum(c.km for c in claims),
              "completed_count": len(claims), "slots": [km if km in by_km else None for km in range(1, 31)], "cells": cells}
    if personal:
        result["strava_connected"] = bool(user.refresh_token)
        result["last_synced_at"] = iso_utc(user.last_synced_at)
        result["sync_error"] = user.last_sync_error
    return result

def leaderboard(db):
    e = edition(db)
    targets = db.scalars(select(DistanceTarget).where(DistanceTarget.edition_id == e.id)).all()
    ps = periods(db, e)
    groups = {}
    for c in db.scalars(select(ChallengeClaim).where(ChallengeClaim.edition_id == e.id)).all():
        groups.setdefault(c.user_id, []).append(c)
    # Reuse the loaded edition for every runner: five queries regardless of user count.
    users = [participant(db, u, groups.get(u.id, []), targets, ps, e=e)
             for u in db.scalars(select(User).options(load_only(User.id, User.name))).all()]
    users.sort(key=lambda u: (-u["total_score"], u["name"].casefold(), u["id"]))
    previous, rank = None, 0
    for i, u in enumerate(users, 1):
        if u["total_score"] != previous:
            rank = i
        u["rank"], previous = rank, u["total_score"]
    return users

def statistics(db):
    e = edition(db)
    totals = dict(db.execute(select(ChallengeClaim.date, func.sum(ChallengeClaim.km))
        .where(ChallengeClaim.edition_id == e.id).group_by(ChallengeClaim.date)).all())
    cumulative, points = 0, []
    first, last = bounds(db, e)
    today = local_today()
    for d in range((last - first).days + 1):
        day = first + timedelta(days=d)
        cumulative += totals.get(day, 0)
        points.append({"date": day.isoformat(), "daily_km": totals.get(day, 0), "total_km": cumulative,
                       "future": day > today})
    return {"total_km": cumulative, "participants": db.scalar(select(func.count(User.id))), "points": points}

def save_draw(db, number, distances, publish=False):
    e = edition(db, lock=True)
    ps = periods(db, e)
    p = next((p for p in ps if p.number == number), None)
    if not p:
        raise HTTPException(404, "Zeitraum nicht gefunden.")
    if p.published_at and local_today() >= p.starts_on:
        raise HTTPException(409, "Diese veröffentlichte Woche hat bereits begonnen und ist gesperrt.")
    if len(distances) != p.capacity or len(set(distances)) != p.capacity:
        raise HTTPException(422, f"Bitte genau {p.capacity} unterschiedliche Distanzen eingeben.")
    used = {e.finale_km}
    for other in ps:
        if other.id != p.id:
            used.update(other.draft_distances)
    if any(type(km) is not int or km < 1 or km > 30 for km in distances) or used.intersection(distances):
        raise HTTPException(422, "Nur freie Distanzen von 1–30 km verwenden; Abschlussdistanz ist reserviert.")
    # Republishing a future draw is allowed only while no result depends on it.
    old = db.scalars(select(DistanceTarget).where(DistanceTarget.period_id == p.id)).all()
    for t in old:
        if db.query(ChallengeClaim).filter_by(target_id=t.id).first():
            raise HTTPException(409, "Diese Auslosung hat bereits Ergebnisse und kann nicht geändert werden.")
        db.delete(t)
    db.flush()
    p.draft_distances = sorted(distances)
    p.published_at = utcnow() if publish else None
    if publish:
        for km in distances:
            db.add(DistanceTarget(edition_id=e.id, period_id=p.id, km=km))
    db.flush()
    rebuild_all(db, e)
    db.commit()
    return configuration(db, admin=True)

def set_finale(db, km):
    e = edition(db, lock=True)
    if km == e.finale_km:
        return configuration(db, admin=True)
    if not 1 <= km <= 30:
        raise HTTPException(422, "Die Abschlussdistanz muss zwischen 1 und 30 km liegen.")
    if local_today() >= finale_date(e):
        raise HTTPException(409, "Der Abschlusslauf hat bereits begonnen.")
    if any(km in p.draft_distances for p in periods(db, e)):
        raise HTTPException(409, "Diese Distanz ist bereits einer Auslosung zugeordnet.")
    t = db.scalar(select(DistanceTarget).where(DistanceTarget.edition_id == e.id, DistanceTarget.period_id.is_(None)))
    if db.query(ChallengeClaim).filter_by(target_id=t.id).first():
        raise HTTPException(409, "Der Abschlusslauf hat bereits Ergebnisse.")
    t.km, e.finale_km = km, km
    db.commit()
    return configuration(db, admin=True)

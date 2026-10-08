"""One monthly calendar for the existing website, scorer and Strava import."""
import os
from datetime import date

CAPACITIES = (8, 7, 7, 7)


class ScheduleConfigurationError(ValueError):
    """Messages contain configuration guidance only, never environment secrets."""


def active_month():
    try:
        month = int(os.getenv("CHALLENGE_MONTH", "11"))
    except ValueError:
        raise ScheduleConfigurationError("CHALLENGE_MONTH must be 10 (October rehearsal) or 11 (November).") from None
    if month not in {10, 11}:
        raise ScheduleConfigurationError("CHALLENGE_MONTH must be 10 (October rehearsal) or 11 (November).")
    return month


def initial_calendar(year, month):
    return [(date(year, month, start), date(year, month, end))
            for start, end in ((1, 8), (9, 15), (16, 22), (23, 29))], date(year, month, 30)


def finale_date(e):
    return e.finale_on or date(e.year, e.month, 30)


def bounds(db, e):
    from sqlalchemy import func, select
    from models.challenge import ChallengePeriod
    start = db.scalar(select(func.min(ChallengePeriod.starts_on)).where(ChallengePeriod.edition_id == e.id))
    if start is None:
        raise ScheduleConfigurationError("Challenge periods have not been initialized.")
    return start, finale_date(e)

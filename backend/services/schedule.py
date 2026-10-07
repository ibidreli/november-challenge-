"""Persisted challenge calendar; test settings never rewrite a production edition."""
import os
from datetime import date, timedelta

CAPACITIES = (8, 7, 7, 7)


class ScheduleConfigurationError(ValueError):
    """Messages contain configuration guidance only, never environment secrets."""


def test_mode_enabled():
    value = os.getenv("CHALLENGE_TEST_MODE", "0")
    if value not in {"0", "1"}:
        raise ScheduleConfigurationError("CHALLENGE_TEST_MODE must be 0 or 1.")
    return value == "1"


def calendar(starts_on, period_days, year):
    if len(period_days) != 4 or any(type(n) is not int or not 1 <= n <= 31 for n in period_days):
        raise ScheduleConfigurationError("Specify four period lengths of 1 to 31 days.")
    finale = starts_on + timedelta(days=sum(period_days))
    if starts_on.year != year or finale.year != year:
        raise ScheduleConfigurationError("All challenge dates must be within CHALLENGE_YEAR.")
    spans = []
    start = starts_on
    for days in period_days:
        end = start + timedelta(days=days - 1)
        spans.append((start, end))
        start = end + timedelta(days=1)
    return spans, finale


def initial_calendar(year, is_test):
    start_value = os.getenv("CHALLENGE_TEST_START_DATE", "").strip()
    days_value = os.getenv("CHALLENGE_TEST_PERIOD_DAYS", "").strip()
    if not is_test:
        if start_value or days_value:
            raise ScheduleConfigurationError("Test calendar settings require CHALLENGE_TEST_MODE=1 and a separate test database.")
        return calendar(date(year, 11, 1), list(CAPACITIES), year)
    try:
        start = date.fromisoformat(start_value or f"{year}-10-01")
        days = [int(n.strip()) for n in days_value.split(",")] if days_value else list(CAPACITIES)
        return calendar(start, days, year)
    except (ValueError, OverflowError) as exc:
        if isinstance(exc, ScheduleConfigurationError):
            raise
        raise ScheduleConfigurationError("Invalid CHALLENGE_TEST_START_DATE or CHALLENGE_TEST_PERIOD_DAYS.") from None


def finale_date(e):
    return e.finale_on or date(e.year, 11, 30)


def bounds(db, e):
    from sqlalchemy import func, select
    from models.challenge import ChallengePeriod
    start = db.scalar(select(func.min(ChallengePeriod.starts_on)).where(ChallengePeriod.edition_id == e.id))
    if start is None:
        raise ScheduleConfigurationError("Challenge periods have not been initialized.")
    return start, finale_date(e)

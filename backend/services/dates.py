"""Calendar helpers shared across the ledger services.

Kept in one place so month arithmetic behaves identically everywhere
(clamping short months, first-of-month normalisation).
"""

import calendar
import datetime as dt


def clamp_day(year: int, month: int, day: int) -> dt.date:
    """``day`` clamped to the last valid day of ``year``-``month``."""
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day, last))


def month_start(d: dt.date) -> dt.date:
    return d.replace(day=1)


def month_end(d: dt.date) -> dt.date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def add_months(d: dt.date, n: int) -> dt.date:
    """First day of the month ``n`` months from ``d``'s month.

    ``n`` may be negative.
    """
    index = d.year * 12 + (d.month - 1) + n
    return dt.date(index // 12, index % 12 + 1, 1)

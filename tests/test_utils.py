
from app import utils

from datetime import datetime, timedelta, UTC
import pytz


DATE_FMT = "%d.%m. %H:%M" 

def test_date_or_none():
    
    date = datetime.now(UTC)
    new_date = utils.date_or_none(date)

    assert date.astimezone(pytz.timezone("Europe/Prague")).strftime(DATE_FMT) == new_date

def test_date_or_none_TBC():

    new_date = utils.date_or_none(None)

    assert new_date == "TBC"

def test_date_or_none_dst():
    date = datetime(2025, month=3, day=29, hour=10)
    no_dst = utils.date_or_none(date)
    assert "29.03. 11:00" == no_dst # +1 hr utc vs cet

    date = datetime(2025, month=3, day=30, hour=10)
    dst = utils.date_or_none(date)
    assert "30.03. 12:00" == dst # +2 hr utc vs cest

def test_date_or_none_end_dst():
    date = datetime(2025, month=10, day=25, hour=10)
    no_dst = utils.date_or_none(date)
    assert "25.10. 12:00" == no_dst # +2 hr utc vs cest

    date = datetime(2025, month=10, day=26, hour=10)

    dst = utils.date_or_none(date)
    assert "26.10. 11:00" == dst # +1 hr utc vs cet


def test_date_or_none_shift():
    date = datetime(2025, month=1, day=1, hour=1)

    new_date = utils.date_or_none(date, shift=timedelta(hours=5))
    assert "01.01. 07:00" == new_date # + 5 + change to CET
 
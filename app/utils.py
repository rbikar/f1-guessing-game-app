from datetime import datetime, timedelta, UTC
from .models import Race, Competitor
import pytz
from app import db
from app.models import Bet, Competitor, Race, RaceResult, User

LOCKS = {
    "quali": lambda race: race.quali_date,
    "race": lambda race: race.race_date,
    "sprint": lambda race: race.sprint_date,
    "dotd": lambda race: race.race_date + timedelta(minutes=50),
}
BET_LOCK_MAP = {
    "QUALI": "quali",
    "SPRINT": "sprint",
    "RACE": "race",
    "SC": "race",
    "FASTEST": "race",
    "BONUS": "race",
    "DRIVERDAY": "dotd",
}


def _db_exec(stmt):
    return db.session.execute(stmt)


def get_current_race():
    stmt = db.select(Race)
    races = _db_exec(stmt).scalars().all()
    now = datetime.now(UTC)
    utc = now.replace(tzinfo=pytz.utc)
    # now = datetime(2023, 12, 4, 18, 00)
    time = utc - timedelta(hours=6)
    candidates = []
    last = []
    last_round = len(races)  ## predelat nejak rozumne
    for race in sorted(races, key=lambda x: x.race_date, reverse=True):
        if race.race_date.replace(tzinfo=pytz.utc) >= time:
            candidates.append(race)
        if race.round == last_round:
            last.append(race)
    if not candidates:
        candidates.extend(last)
    return candidates[-1]


def date_or_none(date, shift=None):
    out = "TBC"
    if date is None:
        return "TBC"

    else:
        out = date.replace(tzinfo=pytz.utc)
        if shift:
            out += shift
        out = out.astimezone(
            pytz.timezone("Europe/Prague")
        )  ### may do this only on frontend and handle only UTC in backend

    return out.strftime("%d.%m. %H:%M")


def get_locks_race(race):
    locks = {}
    now = datetime.now(UTC)
    # now = datetime(2025, 3, 16, 4, 40, tzinfo=UTC)
    utc_now = now.replace(tzinfo=pytz.utc)
    for lock, time_f in LOCKS.items():
        time = time_f(race)
        if time and utc_now >= time.replace(tzinfo=pytz.utc):
            locks[lock] = True
        else:
            locks[lock] = False
    return locks


def lock_or_value(bet_type, bet_value, locks):
    if is_bet_locked(bet_type, locks):
        return "LOCKED"
    return bet_value


def is_bet_locked(bet_type, locks):
    return locks[BET_LOCK_MAP[bet_type]]


###### nasl se bude predelavat
def get_label_attr_season():
    drivers = []
    for num in range(1, 21):
        label = f"{num}."
        attr = f"_{num}d"
        drivers.append({"label": label, "attr": attr})

    constructors = []
    for num in range(1, 11):
        label = f"{num}."
        attr = f"_{num}c"
        constructors.append({"label": label, "attr": attr})

    return drivers, constructors


def get_competitors_codes(type, active=True):
    stmt = db.select(Competitor).where(Competitor.type == type)  # , Competitor.active
    res = _db_exec(stmt)
    codes = [item.code for item in res.scalars()]
    return codes


def get_competitors_names(type):
    stmt = db.select(Competitor).where(Competitor.type == type)  # , Competitor.active
    res = _db_exec(stmt)
    names = [item.name for item in res.scalars()]
    return names

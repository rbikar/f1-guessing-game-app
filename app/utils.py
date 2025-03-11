from datetime import datetime, timedelta, UTC

import pytz

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


def get_current_race(races):
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
    if date is None:
        return "TBC"
    if shift:
        date += shift
    date = date.replace(tzinfo=pytz.utc)
    date = date.astimezone(pytz.timezone("Europe/Prague"))

    return date.strftime("%d.%m. %H:%M")


def get_locks_race(race):
    locks = {}
    now = datetime.now(UTC)
    #now = datetime(2025, 3, 16, 4, 40, tzinfo=UTC)
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

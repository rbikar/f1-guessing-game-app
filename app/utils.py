from datetime import datetime, timedelta

import pytz


def validate_season(from_data):
    pass


def get_current_race(races):
    now = datetime.utcnow()
    utc = now.replace(tzinfo=pytz.utc)
    # now = datetime(2022, 3, 23, 15, 00)
    time = utc - timedelta(hours=6)
    candidates = []
    last = []
    for race in sorted(races, key=lambda x: x.race_start, reverse=True):
        if race.race_start.replace(tzinfo=pytz.utc) >= time:
            candidates.append(race)
        if race.round == "22":
            last.append(race)
    if not candidates:
        candidates.extend(last)
    return candidates[-1]


def date_or_none(date):
    if date is None:
        return "TBC"
    date = date.replace(tzinfo=pytz.utc)
    date = date.astimezone(pytz.timezone("Europe/Prague"))

    return date.strftime("%d.%m. %H:%M")


def get_locks_race(race):
    locks = {}
    now = datetime.utcnow()
    # now = datetime(2022, 3, 23, 15, 00)
    utc_now = now.replace(tzinfo=pytz.utc)

    for attr in ["quali_start", "sprint_start", "race_start"]:
        time = getattr(race, attr)
        if time and utc_now >= time.replace(tzinfo=pytz.utc):
            locks[attr] = True
        else:
            locks[attr] = False

    return locks


lock_attr_map = {
    "quali_start": ["quali"],
    "sprint_start": ["sprint"],
    "race_start": ["first", "second", "third", "fastest_lap", "safety_car", "bonus"],
}


def is_attr_locked(locks, attr):
    for lock, locked in locks.items():
        if attr in lock_attr_map[lock] and locked:
            return True
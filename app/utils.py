from datetime import datetime, timedelta

import pytz


def get_current_race(races):
    now = datetime.utcnow()
    utc = now.replace(tzinfo=pytz.utc)
    # now = datetime(2023, 12, 4, 18, 00)
    time = utc - timedelta(hours=6)
    candidates = []
    last = []
    for race in sorted(races, key=lambda x: x.race_date, reverse=True):
        if race.race_date.replace(tzinfo=pytz.utc) >= time:
            candidates.append(race)
        if race.round == "23":
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
    # now = datetime(2023, 3, 5, 15, 59)
    utc_now = now.replace(tzinfo=pytz.utc)

    for attr in ["qualification_date", "sprint_date", "race_date"]:
        time = getattr(race, attr)
        if time and utc_now >= time.replace(tzinfo=pytz.utc):
            locks[attr] = True
        else:
            locks[attr] = False

    return locks


lock_attr_map = {
    "qualification_date": ["quali"],
    "sprint_date": ["sprint"],
    "race_date": ["first", "second", "third", "fastest_lap", "safety_car", "bonus"],
}


def is_attr_locked(locks, attr):
    for lock, locked in locks.items():
        if attr in lock_attr_map[lock] and locked:
            return True


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


def can_see_guess(lock, user, current_user, admin):
    if admin:
        return True

    if current_user.id == user.id:
        return True

    return lock

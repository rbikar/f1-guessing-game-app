from time import sleep

import requests

API = "https://ergast.com/api/f1/2022"


def get_result(round, rank):
    url = f"{API}/{round}/results/{rank}.json"
    response = requests.get(url)

    data = response.json()
    result = data["MRData"]["RaceTable"]["Races"][0]["Results"][0]["Driver"]["code"]
    return result


def get_q_result(round):
    rank = 1
    url = f"{API}/{round}/qualifying/{rank}.json"
    response = requests.get(url)
    data = response.json()
    result = data["MRData"]["RaceTable"]["Races"][0]["QualifyingResults"][0]["Driver"][
        "code"
    ]
    return result


def get_sprint_result(round):
    rank = 1
    url = f"{API}/{round}/sprint/{rank}.json"
    response = requests.get(url)
    data = response.json()
    result = data["MRData"]["RaceTable"]["Races"][0]["SprintResults"][0]["Driver"][
        "code"
    ]
    return result


def get_fastest_lap(round):
    rank = 1
    url = f"{API}/{round}/fastest/{rank}/results.json"
    response = requests.get(url)
    data = response.json()
    result = data["MRData"]["RaceTable"]["Races"][0]["Results"][0]["Driver"]["code"]
    return result


def get_result_for_round(round, is_sprint=False):
    quali = get_q_result(round)
    sleep(0.5)
    sprint = None
    if is_sprint:
        sprint = get_sprint_result(round)
    sleep(0.5)
    fastest_lap = get_fastest_lap(round)
    sleep(0.5)

    podium = []

    for rank in [1, 2, 3]:
        podium.append(get_result(round, rank))
        sleep(0.5)

    return {
        "quali": quali,
        "sprint": sprint,
        "fastest_lap": fastest_lap,
        "first": podium[0],
        "second": podium[1],
        "third": podium[2],
        "podium": podium,
    }


def evaluate_result_for_user(result, guess):
    attrs = ("first", "second", "third")
    if result:
        podium = [getattr(result, attr) for attr in attrs]
    else:
        podium = []
    results_map_podium = {attr: 0.0 for attr in attrs}

    for index, attr in enumerate(attrs):
        value = getattr(guess, attr)
        if value in podium:
            results_map_podium[attr] += 0.5
        if podium and value == podium[index]:
            results_map_podium[attr] += 0.5
            if attr == "first":
                results_map_podium[attr] += 1.0

    attrs = ["fastest_lap", "quali", "safety_car"]
    if result and result.sprint:
        attrs.append("sprint")

    results_map_other = {attr: 0.0 for attr in attrs}

    for attr in attrs:
        guess_value = getattr(guess, attr)  # value of user guess for race
        if result:
            result_value = getattr(result, attr)  # value of race result
            if attr == "safety_car":
                try:
                    guess_value = float(guess_value)
                    result_value = float(result_value)
                except TypeError:
                    continue
            if guess_value == result_value:
                results_map_other[attr] += 1.0

    if guess.bonus_ok:
        results_map_other["bonus"] = 1.0
    else:
        results_map_other["bonus"] = 0.0

    results_map_podium.update(results_map_other)

    return results_map_podium, sum([float(num) for num in results_map_podium.values()])


def get_drivers_standings():
    url = f"{API}/driverStandings.json"
    response = requests.get(url)
    data = response.json()

    standings = data["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    to_db_items = []
    for item in standings:
        position = item["position"]
        points = item["points"]
        driver = item["Driver"]["code"]
        if driver in ("HUL", "DEV"):
            continue

        to_db_items.append({"position": position, "points": points, "driver": driver})

    return to_db_items


CONSTRUCTOR_ID_CODE_MAP = {
    "red_bull": "REB",
    "ferrari": "FER",
    "mercedes": "MER",
    "alpine": "ALP",
    "mclaren": "MCL",
    "alfa": "ALF",
    "aston_martin": "ASM",
    "haas": "HAS",
    "alphatauri": "ALT",
    "williams": "WIL",
}

# TODO new table for constructor: API_ID-CODE-FULLNAME


def get_constructors_standings():
    url = f"{API}/constructorStandings.json"
    response = requests.get(url)
    data = response.json()

    standings = data["MRData"]["StandingsTable"]["StandingsLists"][0][
        "ConstructorStandings"
    ]
    to_db_items = []
    for item in standings:
        position = item["position"]
        points = item["points"]
        team = CONSTRUCTOR_ID_CODE_MAP[item["Constructor"]["constructorId"]]
        to_db_items.append({"position": position, "points": points, "team": team})

    return to_db_items


# SORT BY REAL TEAM STANDIGS
# for pos in range...staci
#     item[pos]
team_drivers_map = {
    "MER": ("HAM", "RUS"),
    "REB": ("VER", "PER"),
    "FER": ("LEC", "SAI"),
    "MCL": ("RIC", "NOR"),
    "ALP": ("ALO", "OCO"),
    "ALF": ("ZHO", "BOT"),
    "ALT": ("TSU", "GAS"),
    "HAS": ("MSC", "MAG"),
    "WIL": ("LAT", "ALB"),
    "AST": ("VET", "STR"),
}


def team_match_results(bet, results):
    out = {}
    for team, drivers in team_drivers_map.items():
        first_driver_bet = get_position_from_season_bet(drivers[0], bet)
        first_driver_stdgs = get_position_for_driver_from_standings(drivers[0], results)
        second_driver_bet = get_position_from_season_bet(drivers[1], bet)
        second_driver_stdgs = get_position_for_driver_from_standings(
            drivers[1], results
        )
        if first_driver_bet is None or second_driver_bet is None:
            continue

        # if 1st driver is better -> automatically it means that second driver is worse
        first_better_bet = first_driver_bet < second_driver_bet
        first_better_stdgs = first_driver_stdgs < second_driver_stdgs

        hit = team_match_hit(first_better_bet, first_better_stdgs)
        out[team] = {
            "points": 1 if hit else 0,
            "bet": {drivers[0]: first_better_bet, drivers[1]: not first_better_bet},
            "stdgs": {
                drivers[0]: first_better_stdgs,
                drivers[1]: not first_better_stdgs,
            },
        }
    return out


def team_match_hit(bet, result):
    return bet is result


def get_position_for_driver_from_standings(driver, results):
    for item in results:
        if item.name == driver:
            return int(item.position)


def get_position_from_season_bet(driver, bet):
    if bet is None:
        return "N/A"
    for pos in range(1, 21):
        attr = f"_{pos}d"
        bet_on_position = getattr(bet, attr)
        if bet_on_position == driver:
            return int(pos)


def make_results_map(results):
    results_map = {}
    for item in results:
        results_map[int(item.position)] = item.name

    return results_map


def season_result(bet, results_map, std_type=None):
    # drivers
    # 1st place +10
    # presny tip +2
    # vzajemny soubot +1
    # teams
    # 1st place +5
    # presna polozka +2
    pointing = {
        "drivers": {
            "champion": 10,
            "hit": 2,
            "team_match": 1,
            "type": "d",
            "range": 20,
        },
        "teams": {
            "champion": 5,
            "hit": 2,
            "type": "c",
            "range": 10,
        },
    }

    result_to_display = {}  # position, typ, body
    cfg = pointing[std_type.lower()]

    for pos in range(1, cfg["range"] + 1):
        points = 0
        attr = f"_{pos}{cfg['type']}"
        if bet is None:
            bet_on_position="N/S"
        else:
            bet_on_position = getattr(bet, attr)

        if bet_on_position == results_map[pos]:
            points += cfg["hit"]
            if pos == 1:
                points += cfg["champion"]

        result_to_display[pos] = {
            "points": points,
            "type": cfg["type"],
        }

    return result_to_display

import requests
from time import sleep

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
    results_map_podium = {attr: 0 for attr in attrs}

    for index, attr in enumerate(attrs):
        value = getattr(guess, attr)
        if value in podium:
            results_map_podium[attr] += 0.5
        if podium and value == podium[index]:
            results_map_podium[attr] += 0.5
            if attr == "first":
                results_map_podium[attr] += 1

    attrs = ["fastest_lap", "quali", "safety_car"]
    if result and result.sprint:
        attrs.append("sprint")

    results_map_other = {attr: 0 for attr in attrs}

    for attr in attrs:
        value = getattr(guess, attr)
        if result:
            guess_value = getattr(result, attr)
            if attr == "safety_car" and guess_value and value:
                value = float(value)
                guess_value = float(guess_value)
            if guess_value == value:
                results_map_other[attr] += 1

    if guess.bonus_ok:
        results_map_other["bonus"] = 1
    else:
        results_map_other["bonus"] = 0

    results_map_podium.update(results_map_other)

    return results_map_podium, sum([float(num) for num in results_map_podium.values()])

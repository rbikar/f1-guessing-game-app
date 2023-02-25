import json

import requests

API = "https://ergast.com/api/f1/2022"


# http://ergast.com/api/f1/2010/1/fastest/1/results  # fastest lap
# http://ergast.com/api/f1/2021/10/sprint
# https://ergast.com/api/f1/2021/10/sprint/1
# http://ergast.com/api/f1/2008/5/qualifying/1

# https://ergast.com/api/f1/current/last/results/1
# https://ergast.com/api/f1/current/last/results/2
# https://ergast.com/api/f1/current/last/results/3


# safety car
# bonusovka


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


from time import sleep

current_round = 1
print(get_q_result(1))
print(get_fastest_lap(1))

exit(0)

for rank in [1, 2, 3]:
    print(f"{rank}:{get_result(current_round, rank)}")
    sleep(0.5)


def guess_result():
    podium = ("VER", "LEC", "HAM")
    guess = object()

    attrs = ("first", "second", "third")  ##sprint if type==SPRINT and kvalda
    results_map_podium = {(attr, 0) for attr in attrs}

    for index, attr in enumerate(attrs):
        value = getattr(guess, attr)
        if value in podium:
            results_map_podium[attr] += 0.5
        if value == podium[index]:
            results_map_podium[attr] += 0.5
            if attr == "first":
                results_map_podium[attr] += 1

    attrs = "fastest_lap"
    results_map_other = {(attr, 0) for attr in attrs}

    results = {}
    for attr in attrs:
        value = getattr(guess, attr)
        if value == str(results[attr]):
            results_map_other[attr] += 1

    ### manualni
    attrs = ("safety_car", "bonus")
    results_map_manul = {(attr, 0) for attr in attrs}

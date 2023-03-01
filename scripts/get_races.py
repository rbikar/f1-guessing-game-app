import requests
from bs4 import BeautifulSoup
import json


API = "https://ergast.com/api/f1/2023"
import pytz
from datetime import datetime

round_f1name_map = {
    1: "Bahrain",
    2: "Saudi_Arabia",
    3: "Australia",
    4: "EmiliaRomagna",
    5: "Miami",
    6: "Spain",
    7: "Monaco",
    8: "Azerbaijan",
    9: "Canada",
    10: "Great_Britain",
    11: "Austria",
    12: "France",
    13: "Hungary",
    14: "Belgium",
    15: "Netherlands",
    16: "Italy",
    17: "Singapore",
    18: "Japan",
    19: "United_States",
    20: "Mexico",
    21: "Brazil",
    22: "United_Arab_Emirates",
}


def get_schedule_for_season():
    url = API + ".json"
    response = requests.get(url)

    data = response.json()
    out = []
    races = data["MRData"]["RaceTable"]["Races"]
    for race in races:
        quali_defined = race.get("Qualifying", {}).get("date", {})
        if quali_defined:
            q_time = race["Qualifying"]["date"] + "T" + race["Qualifying"]["time"][:-1]
        else:
            q_time = "TBC"

        sprint_defined = race.get("Sprint", {}).get("date", {})
        if sprint_defined:
            sprint_time = race["Sprint"]["date"] + "T" + race["Sprint"]["time"][:-1]
        else:
            sprint_time = "TBC"

        item = {
            "short_name": race["Circuit"]["circuitId"],
            "name": race["raceName"],
            "round": race["round"],
            "race_start": race["date"] + "T" + race["time"][:-1],  ### already in UTC
            "type": "NORMAL"
            if not sprint_defined
            else "SPRINT",  # Imola, Redbull ring, Brazil
            "quali_start": q_time,  ### already in UTC
            "sprint_start": sprint_time,  ### already in UTC
        }
        out.append(item)

    return out


def get_schedule_from_f1com(races):
    for race in races:
        name = round_f1name_map[int(race["round"])]
        url = f"https://www.formula1.com/en/racing/2022/{name}.html"
        data = requests.get(url)
        html_doc = data.text
        soup = BeautifulSoup(html_doc, "html.parser")
        qualifying_el = soup.find(class_="row js-qualifying")
        if qualifying_el:
            date = qualifying_el.attrs["data-start-time"]
            gmt_offset = qualifying_el.attrs["data-gmt-offset"]
            race["quali_start"] = get_utc_from_local(date, gmt_offset)

        sprint_el = soup.find(class_="row js-sprint")  ### check the class name
        if sprint_el:
            date = qualifying_el.attrs["data-start-time"]
            gmt_offset = qualifying_el.attrs["data-gmt-offset"]
            race["sprint_start"] = get_utc_from_local(date, gmt_offset)


def get_utc_from_local(date, gmt_offset):
    if "TBC" in date:
        utc_date = "TBC"
    else:
        date_local = datetime.fromisoformat(
            date + gmt_offset
        )  # "'2022-03-19T18:00:00+03:00'"
        date_utc = date_local.astimezone(pytz.timezone("UTC"))
        utc_date = date_utc.isoformat()
    return utc_date


races = get_schedule_for_season()
# get_schedule_from_f1com(races)

with open("races.json", "w") as f:
    json.dump(races, f)

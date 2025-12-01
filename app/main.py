import enum
import os
from collections import OrderedDict, defaultdict
from time import sleep
from datetime import timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import update, select, func
import pycountry
from app import db
from app.models import Bet, Competitor, Race, RaceResult, User
from app.ergast_client.client import Client
from .results import (
    evaluate_result_for_user,
    get_constructors_standings,
    get_drivers_standings,
    get_result_for_round,
    make_results_map,
    season_result,
    team_match_results,
    eval_bet,
    SUNDAY_TYPES,
)
from .utils import (
    date_or_none,
    get_current_race,
    get_label_attr_season,
    get_locks_race,
    is_bet_locked,
    get_competitors_codes,
    get_competitors_names,
    _db_exec,
)

MESSAGES = {
    "BET_SAVED": "Tip v pořádku uložen",
}

KEY_TYPE_RANK_MAP = {
    "quali": ("QUALI", None),
    "sprint": ("SPRINT", None),
    "first": ("RACE", 1),
    "second": ("RACE", 2),
    "third": ("RACE", 3),
    "safety_car": ("SC", None),
    "fastest_lap": ("FASTEST", None),
    "bonus": ("BONUS", None),
    "driver_of_the_day": ("DRIVERDAY", None),
}
MAX_JOKERS = 3


BET_TYPE_SEASON = {"driver": "SEASON_DRIVER", "team": "SEASON_TEAM"}
BET_FORM_KEYS = {f"select_driver_{i}" for i in range(1, 21)} | {
    f"select_team_{i}" for i in range(1, 11)
}

TEAM_MATCH_DRIVERS_MAP = {
    "MER": ("ANT", "RUS"),
    "REB": ("VER", "TSU"),
    "FER": ("LEC", "HAM"),
    "MCL": ("NOR", "PIA"),
    "ALP": ("GAS", "DOO"),
    "KIK": ("HUL", "BOR"),
    "RBS": ("LAW", "HAD"),
    "HAS": ("OCO", "BEA"),
    "WIL": ("SAI", "ALB"),
    "ASM": ("ALO", "STR"),
}


main = Blueprint("main", __name__)


@main.route("/health")
def health():
    return {"status": "OK"}


@main.route("/")
def index():
    return render_template("index.html")


### not used - maybe improve?
@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", name=current_user.username)


@main.route("/race")
@login_required
def race_current():
    race = get_current_race()
    return redirect(url_for(".race", external_circuit_id=race.ext_id))


@main.route("/race/<string:external_circuit_id>", methods=["GET", "POST"])
@login_required
def race(external_circuit_id):
    ##TODO create default bets foa all users/races
    drivers_codes = get_competitors_codes(type="DRIVER")

    stmt = db.select(Race).where(Race.ext_id == external_circuit_id)
    res = _db_exec(stmt)
    race = res.scalar()  # first?

    stmt = db.select(Bet).where(Bet.race_id == race.id, Bet.user_id == current_user.id)
    res = _db_exec(stmt)
    user_bet = {}
    for item in res.scalars():
        if item.type == "RACE" and item.rank == 1:
            user_bet["joker"] = True if item.extra == "JOKER" else None
        if item.rank:
            user_bet[f"{item.type.lower()}_{item.rank}"] = item.value
        else:
            user_bet[f"{item.type.lower()}"] = item.value
    locks = get_locks_race(race)
    if request.method == "POST":
        bet_data = []
        for key in KEY_TYPE_RANK_MAP:

            if is_bet_locked(KEY_TYPE_RANK_MAP[key][0], locks):
                continue
            # FIX SETTING JOKER FOR DRIVER OF THE DAY
            bet = {
                "type": KEY_TYPE_RANK_MAP[key][0],
                "rank": KEY_TYPE_RANK_MAP[key][1],
                "value": request.form.get(key) or None,
                "extra": (
                    "JOKER"
                    if KEY_TYPE_RANK_MAP[key][0] in SUNDAY_TYPES
                    and request.form.get("joker")
                    else None
                ),
                "race_id": race.id,
                "user_id": current_user.id,
            }
            bet_data.append(bet)

        if user_bet:
            for item in bet_data:
                stmt = (
                    update(Bet)
                    .where(
                        Bet.user_id == current_user.id,
                        Bet.race_id == race.id,
                        Bet.type == item["type"],
                        Bet.rank == item["rank"],
                    )
                    .values(extra=item["extra"], value=item["value"], rank=item["rank"])
                    .returning(Bet)
                )
                if not _db_exec(stmt).scalar():
                    db.session.add(Bet.from_data(item))

        else:  # store whole bet even with empty bets
            db.session.add_all(Bet.from_data(bet_data))

        db.session.commit()
        flash(MESSAGES["BET_SAVED"])
        return redirect(url_for(".race", external_circuit_id=race.ext_id))

    response = {
        "drivers": drivers_codes,
        "bet": user_bet,
        "locks": locks,
        "race": race,
        "country_code": get_country_code(race.country),
        "start_times": {
            "q_start": date_or_none(race.quali_date),
            "s_start": date_or_none(race.sprint_date) if race.sprint_date else None,
            "r_start": date_or_none(race.race_date),
            "dod_end": date_or_none(race.race_date, shift=timedelta(minutes=50)),
        },
        "joker_stats": {
            "available": MAX_JOKERS - get_joker_stats_for_uses(current_user.id),
            "max": MAX_JOKERS,
        },
    }
    # print(response)
    return render_template("race.html", data=response)


def get_country_code(country):
    out = ""
    if len(country) == 2:
        out = country
    else:
        _country = pycountry.countries.get(name=country) or pycountry.countries.get(
            alpha_3=country
        )
        if _country:
            out = _country.alpha_2.lower()

    return out


def get_joker_stats_for_uses(user_id):
    stmt = (
        select(func.count())
        .select_from(Bet)
        .where(
            Bet.user_id == user_id,
            Bet.type == "RACE",
            Bet.rank == 1,
            Bet.extra == "JOKER",
        )
    )
    return _db_exec(stmt).scalar()


@main.route("/races", methods=["GET"])
@login_required
def races():
    ### TODO send only json response to template, make table in JS
    def get_row(race):
        return {
            "name": race.name.replace("Grand Prix", "GP"),
            "s": date_or_none(race.sprint_date) if race.sprint_date else "-----",
            "q": date_or_none(race.quali_date),
            "r": date_or_none(race.race_date),
            "external_circuit_id": race.ext_id,
        }

    stmt = db.select(Race)
    races = _db_exec(stmt).scalars().all()
    currrent_race = get_current_race()
    table_head = ["F1 2025", "SPRINT", "KVALIFIKACE", "ZÁVOD", ""]
    finished = []
    current = []
    upcoming = []
    switch = False
    rows = {}
    for race in sorted(races, key=lambda x: x.race_date):
        if race.ext_id == currrent_race.ext_id:
            current.append(get_row(race))
            switch = True
            continue
        if not switch:
            # finished
            finished.append(get_row(race))
        if switch:
            upcoming.append(get_row(race))

    rows["upcoming"] = upcoming
    rows["current"] = current
    rows["finished"] = finished

    return render_template("races.html", table_head=table_head, rows=rows)


@main.route("/season", methods=["GET", "POST"])
@login_required
def season():
    locked = bool(os.getenv("SEASON_LOCK", ""))
    drivers = get_competitors_codes(type="DRIVER")
    teams = get_competitors_names(type="TEAM")

    ### toto pak do pryc :) nebo nechatp ro pro kontrolu
    # assert len(drivers) == 20
    assert len(teams) == 10

    stmt = select(Bet).where(
        Bet.user_id == current_user.id,
        ((Bet.type == "SEASON_DRIVER") | (Bet.type == "SEASON_TEAM")),
    )
    user_bet = _db_exec(stmt).scalars().all()

    if request.method == "POST":
        bet_data = []
        for key in BET_FORM_KEYS:

            # keys: select_<type>_<rank>
            _, bet_type, rank = key.split("_")
            bet = {
                "type": BET_TYPE_SEASON[bet_type.lower()],
                "rank": int(rank),
                "value": request.form.get(key) or None,
                "user_id": current_user.id,
            }
            bet_data.append(bet)

        if user_bet:
            for item in bet_data:
                stmt = (
                    update(Bet)
                    .where(
                        Bet.user_id == current_user.id,
                        Bet.type == item["type"],
                        Bet.rank == item["rank"],
                    )
                    .values(value=item["value"], rank=item["rank"])
                    .returning(Bet)
                )
                if not _db_exec(stmt).scalar():
                    db.session.add(Bet.from_data(item))

        else:  # store whole bet even with empty bets
            db.session.add_all(Bet.from_data(bet_data))

        db.session.commit()
        flash("Tip v pořádku uložen")
        return redirect(url_for("main.season"))

    bets = {
        "DRIVER": {
            item.rank: item.value for item in user_bet if item.type == "SEASON_DRIVER"
        },
        "TEAM": {
            item.rank: item.value for item in user_bet if item.type == "SEASON_TEAM"
        },
    }
    response = {
        "bets": bets,
        "drivers": drivers,
        "teams": teams,
        "locked": locked,
    }

    return render_template(
        "season.html",
        data=response,
    )


@main.route("/bet_result")
@login_required
def bet_result_current():
    race = get_current_race()
    return redirect(url_for(".bet_result", external_circuit_id=race.ext_id))


@main.route("/bet_result/<string:external_circuit_id>", methods=["GET"])
@login_required
def bet_result(external_circuit_id):
    stmt = select(Race).where(Race.ext_id == external_circuit_id)

    race = _db_exec(stmt).scalar()
    out_results = {"race_id": race.ext_id, "race_name": race.name, "results": []}
    stmt = select(Competitor)
    competitors = {item.id: item.code for item in _db_exec(stmt).scalars().all()}

    for item in race.race_results:

        to_add = {
            "type": f"{item.type}{"_" + str(item.rank) if item.rank is not None else ""}",
            "val": competitors.get(item.competitor_id)
            or item.value,  ###pridat  relationship do tabulky raceresult
        }

        out_results["results"].append(to_add)

    stmt = select(User)
    users = _db_exec(stmt).scalars().all()

    out_users = []
    locks = get_locks_race(race)
    for user in users:
        stmt = select(Bet).where(Bet.race_id == race.id, Bet.user_id == user.id)
        res = _db_exec(stmt).scalars().all()

        item = {"username": user.username, "race": external_circuit_id, "bets": []}
        total = 0
        for bet in res:
            if bet.value is None:
                value = None
            elif current_user.id == user.id:
                value = bet.value
            elif not is_bet_locked(bet.type, locks) and current_user.id != user.id:
                value = "LOCKED"
            else:
                value = bet.value

            item["bets"].append(
                {
                    "type": f"{bet.type}{"_" + str(bet.rank) if bet.rank is not None else ""}",
                    "points": bet.result,
                    "value": value,
                    "extra": bet.extra,
                }
            )
            total += bet.result

        item["total_points"] = total
        out_users.append(item)

    response = {
        "race": out_results,
        "users": out_users,
    }
    return render_template("bet_result.html", data=response)


@main.route("/guess_overview/season")
@login_required
def guess_overview_season():
    # results_available = bool(os.getenv("SEASON_RESULTS", ""))
    # if not results_available:
    #    return render_template("wip.html")

    out_results = {"results": []}

    ### TODO SEASON standings - to add to competitors table + computation of current point for playewrs

    stmt = select(User)
    users = _db_exec(stmt).scalars().all()

    out_users = []
    locked = bool(os.getenv("SEASON_LOCK", ""))

    for user in users:
        stmt = select(Bet).where(
            Bet.user_id == user.id,
            ((Bet.type == "SEASON_DRIVER") | (Bet.type == "SEASON_TEAM")),
        )
        res = _db_exec(stmt).scalars().all()

        item = {"username": user.username, "bets": []}
        total_drivers = 0
        total_teams = 0
        total_team_match = 0
        for bet in res:
            if bet.value is None:
                value = None
            elif current_user.id == user.id:
                value = bet.value
            elif not locked and current_user.id != user.id:
                value = "LOCKED"
            else:
                value = bet.value

            item["bets"].append(
                {
                    "type": f"{bet.type}{"_" + str(bet.rank) if bet.rank is not None else ""}",
                    "points": bet.result,
                    "value": value,
                    "match_ok": bet.extra == "MATCH OK",
                }
            )

            if bet.type == "SEASON_DRIVER":
                total_drivers += bet.result
                if bet.extra == "MATCH OK":
                    total_team_match += 0.5
            elif bet.type == "SEASON_TEAM":
                total_teams += bet.result
            else:
                continue

        item["total_points_drivers"] = total_drivers
        item["total_points_teams"] = total_teams
        item["total_points_team_match"] = total_team_match
        out_users.append(item)

    results_drivers_db = sorted(
        list(get_driver_adjusted_standings().values()), key=lambda x: x["position"]
    )
    results_drivers = []
    for i in range(1, 21):
        item = {
            "type": f"SEASON_DRIVER_{i}",
            "value": results_drivers_db[i - 1]["code"],
        }
        results_drivers.append(item)
    results_teams_db = sorted(
        list(get_constr_standings().values()), key=lambda x: x.position
    )
    results_teams = []
    for i in range(1, 11):
        item = {
            "type": f"SEASON_TEAM_{i}",
            "value": constr_ext_id_name_map[results_teams_db[i - 1].ext_id],
        }
        results_teams.append(item)

    response = {
        "season": {
            "drivers": results_drivers,
            "teams": results_teams,
        },
        "users": out_users,
    }

    return render_template("guess_overview_season.html", data=response)


def _get_sum_user(data):
    out = 0
    if data:
        for item in data.values():
            out += item["points"]

    return out


def season_row_driver(order, user_guess_map, season_results):
    row = []
    attr = f"_{order}d"
    for user, guess in user_guess_map.items():
        if guess:
            value = getattr(guess, attr)
        else:
            value = None

        points = season_results[user]["data"]["drivers"][order]["points"]
        row.append(value if value else "N")
        row.append(f"{points}")

    return row


def season_row_constr(order, user_guess_map, season_results):
    row = []
    attr = f"_{order}c"
    for user, guess in user_guess_map.items():
        if guess:
            value = getattr(guess, attr)
        else:
            value = None

        points = season_results[user]["data"]["teams"][order]["points"]
        row.append(value if value else "N")
        row.append(f"{points}")

    return row


def get_team_match_stdg_result(season_results, team):
    for item in season_results.values():
        result = item["data"]["team_match"].get(team, {}).get("stdgs", {})
        if result:
            for driver, res in result.items():
                if res == True:
                    better = driver
                if res == False:
                    worse = driver
            return f"{better} > {worse}"
        else:
            return "?"


def team_match_row(team, users, season_results):
    row = []
    for user in users:  # user are sorted
        result_for_user = (
            season_results[user.username]["data"]["team_match"].get(team) or None
        )
        #        {'points': 0, 'bet': {'HAM': False, 'RUS': True}, 'stdgs': {'HAM': False, 'RUS': True}}
        result = result_for_user["bet"]
        for driver, res in result.items():
            if res == True:
                better = driver
            if res == False:
                worse = driver
        if result_for_user:
            row.append(f"{better} - {worse}")
            row.append(f"{result_for_user['points']}")

    return row


def get_user_guess_map(users):
    user_guess_map = OrderedDict()
    for user in sorted(users, key=lambda x: x.username):
        guess = (
            db.session.query(SeasonGuess).filter(SeasonGuess.user_id == user.id).first()
        )
        user_guess_map[user.username] = guess

    return user_guess_map


def get_attr_value(guess_set, guess, attr, lock, current_user_id, user):
    if not guess_set:
        value = "N"
    else:
        value = getattr(guess, attr)
        if value is None or value == "":
            value = "N"  ### not set
        elif current_user_id != user.id and not lock:
            value = "L"  ### locked for other user

    return value


def get_season_result_driver(username, season_results):
    out = 0
    for data in season_results[username]["data"]["drivers"].values():
        out += data["points"]

    return out


def get_season_result_constr(username, season_results):
    out = 0
    for data in season_results[username]["data"]["teams"].values():
        out += data["points"]

    return out


def get_season_team_match(username, season_results):
    out = 0
    for data in season_results[username]["data"]["team_match"].values():
        out += data["points"]

    return out


@main.route("/rules")
@login_required
def rules():
    return render_template("rules.html")


#### admin only / TODO move to different router


@main.route("/result/<string:external_circuit_id>/evaluate", methods=["GET", "POST"])
@login_required
def evaluate_result_post(external_circuit_id):
    if current_user.role != "ADMIN":
        raise Exception

    stmt = select(Race).where(Race.ext_id == external_circuit_id)
    race = _db_exec(stmt).scalar()

    stmt = select(RaceResult).where(
        RaceResult.race_id == race.id, RaceResult.type == "BONUS"
    )
    bonus_answer = _db_exec(stmt).scalar().value

    bonus_question = race.bonus_bet

    bonus_table = [bonus_question, bonus_answer]

    stmt = select(Bet).where(Bet.race_id == race.id, Bet.type == "BONUS")
    bets = _db_exec(stmt).scalars().all()

    thead = ["USERNAME", "BONUSGUESS"]
    rows = []
    for item in bets:
        bonus_guess = item.value
        user = item.user

        rows.append([user.username, bonus_guess, user.id])

    if request.method == "POST":
        users = _db_exec(select(User)).scalars().all()

        stmt = select(RaceResult).where(RaceResult.race_id == race.id)
        race_result_map = {}

        for r in _db_exec(stmt).scalars().all():
            key = f"{r.type}_{r.rank}" if r.rank else r.type
            race_result_map[key] = r

        for user in users:
            bonus_ok = True if request.form.get(str(user.id), "") == "on" else False
            stmt = select(Bet).where(
                Bet.race_id == race.id, Bet.type == "BONUS", Bet.user_id == user.id
            )
            bet = _db_exec(stmt).scalar()

            if bet and bonus_ok:
                bet.result = 2
                if bet.extra and bet.extra == "JOKER":
                    bet.result *= 2
                db.session.commit()

            for type_rank in KEY_TYPE_RANK_MAP.values():
                type, rank = type_rank

                if type == "BONUS":
                    continue
                # import pdb; pdb.set_trace()
                if type == "SPRINT" and race.type != "SPRINT":
                    continue
                stmt = select(Bet).where(
                    Bet.race_id == race.id,
                    Bet.type == type,
                    Bet.rank == rank,
                    Bet.user_id == user.id,
                )
                bet = _db_exec(stmt).scalar()

                bet.result = eval_bet(bet, race_result_map)
                db.session.commit()

    return render_template(
        "evaluate.html", race=race, thead=thead, rows=rows, bonus_table=bonus_table
    )


@main.route("/result/<string:external_circuit_id>", methods=["GET", "POST"])
@login_required
def load_results(external_circuit_id):
    if current_user.role != "ADMIN":
        raise Exception

    stmt = select(Race).where(Race.ext_id == external_circuit_id)
    race = _db_exec(stmt).scalar()

    stmt = select(RaceResult).where(RaceResult.race_id == race.id)
    results = _db_exec(stmt).scalars().all()
    loaded = False
    if results[0].value is not None:
        loaded = True
        flash("ALREADY LOADED")
    else:
        flash(f"RESULT FOR {external_circuit_id} NOT LOADED!")

    if request.method == "POST":
        ## do update
        new_results = []
        result_data = get_result_for_round(
            race.round, True if race.sprint_date else False
        )

        for key in KEY_TYPE_RANK_MAP:
            if key in result_data:
                value = result_data[key]

            else:
                value = request.form.get(key)

            item = {
                "type": KEY_TYPE_RANK_MAP[key][0],
                "rank": KEY_TYPE_RANK_MAP[key][
                    1
                ],  ### competitor ID nebo value prilezitostne
                "value": value,
                "race_id": race.id,
            }
            new_results.append(item)

        if results:
            for item in new_results:
                if item["type"] == "SPRINT" and race.type != "SPRINT":
                    continue
                stmt = (
                    update(RaceResult)
                    .where(
                        RaceResult.race_id == race.id,
                        RaceResult.type == item["type"],
                        RaceResult.rank == item["rank"],
                    )
                    .values(value=item["value"], rank=item["rank"])
                    .returning(RaceResult)
                )
                if not _db_exec(stmt).scalar():
                    db.session.add(RaceResult.from_data(item))

        else:
            db.session.add_all(RaceResult.from_data(new_results))
        db.session.commit()
        flash("RESULT SAVED TO DB")

    return render_template(
        "result.html",
        race=race,
        drivers=get_competitors_codes(type="DRIVER"),
        loaded=loaded,
    )


@main.route("/results/load/", methods=["GET"])
@login_required
def load_standings_route():
    if current_user.role != "ADMIN":
        raise Exception
    message = load_standings()
    return redirect(url_for(".top_players", message=message))


@main.route("/results/", methods=["GET"])
@login_required
def results_table(message=None):
    if current_user.role != "ADMIN":
        raise Exception
    races = db.session.query(Race).all()

    def get_row(race):
        return {
            "name": race.name.replace("Grand Prix", "GP"),
            "short_name": race.external_circuit_id,
        }

    rows = []
    for race in races:
        row = get_row(race)
        rows.append(row)
    message = request.args.get("message")
    if message:
        flash(f"STANDINGS: {message}")

    return render_template("results_table.html", rows=rows)


constr_ext_id_name_map = {
    "alpine": "Alpine F1 Team",
    "aston_martin": "Aston Martin",
    "ferrari": "Ferrari",
    "haas": "Haas F1 Team",
    "mclaren": "McLaren",
    "mercedes": "Mercedes",
    "rb": "RB F1 Team",
    "red_bull": "Red Bull",
    "sauber": "Sauber",
    "williams": "Williams",
    "Alpine F1 Team": "alpine",
    "Aston Martin": "aston_martin",
    "Ferrari": "ferrari",
    "Haas F1 Team": "haas",
    "McLaren": "mclaren",
    "Mercedes": "mercedes",
    "RB F1 Team": "rb",
    "Red Bull": "red_bull",
    "Sauber": "sauber",
    "Williams": "williams",
}


def compute_driver_season(user, standings):
    stmt = select(Bet).where(Bet.user_id == user.id, Bet.type == "SEASON_DRIVER")
    bets = _db_exec(stmt).scalars().all()
    for bet in bets:
        driver_code_bet = bet.value
        if (pos := standings[driver_code_bet]["position"]) == bet.rank:
            if pos == 1:
                bet.result = 12
            else:
                bet.result = 2


def compute_constr_result(user, standings):
    stmt = select(Bet).where(Bet.user_id == user.id, Bet.type == "SEASON_TEAM")
    bets = _db_exec(stmt).scalars().all()
    for bet in bets:
        constructor_ext_id_bet = constr_ext_id_name_map[bet.value]
        if (pos := standings[constructor_ext_id_bet].position) == bet.rank:
            if pos == 1:
                bet.result = 7
            else:
                bet.result = 2


def compute_team_match_result(user, standings):
    stmt = select(Bet).where(Bet.user_id == user.id, Bet.type == "SEASON_DRIVER")
    bets = _db_exec(stmt).scalars().all()
    bets_map = {bet.value: bet for bet in bets}

    for pair in TEAM_MATCH_DRIVERS_MAP.values():
        print(pair)
        sorted_pair = sorted(pair)
        first_driver = sorted_pair[0]
        second_driver = sorted_pair[1]
        first_driver_stdgs = standings[first_driver]["position"]
        second_driver_stdgs = standings[second_driver]["position"]
        print("LIVE", first_driver_stdgs, second_driver_stdgs)

        first_driver_bet = bets_map[first_driver].rank
        second_driver_bet = bets_map[second_driver].rank
        print("BET", first_driver_bet, second_driver_bet)
        first_better_bet = first_driver_bet < second_driver_bet
        first_better_stdgs = first_driver_stdgs < second_driver_stdgs
        hit = first_better_bet is first_better_stdgs
        print(f"HIT: {hit}")
        if hit:
            bets_map[first_driver].extra = "MATCH OK"
            bets_map[second_driver].extra = "MATCH OK"
        else:
            bets_map[first_driver].extra = "MATCH NOT OK"
            bets_map[second_driver].extra = "MATCH NOT OK"


@main.route("/bet_overview")
@login_required
def bet_overview():
    # TODO 2025
    return render_template("wip.html")


@main.route("/top_players")
@login_required
def top_players():
    # TODO 2025 (season)
    """
    {
    [
    "username": "XXX",
    "points": 123,
    "order": 1 - should be ordered ideally

    ]
    }

    """
    # stmt = select(Bet).where(Bet.type != "SEASON_DRIVER" or Bet.type != "SEASON_TEAM")
    stmt = select(Bet)
    # improvement: do sum and group by user on db side
    all_bets = _db_exec(stmt).scalars().all()

    user_result_map_races = {}
    user_result_map_season = {}
    user_result_map_total = {}
    for bet in all_bets:
        user_result_map_races.setdefault(
            bet.user.username,
            {
                "username": bet.user.username,
                "points": 0,
                "order": 0,
            },
        )
        user_result_map_season.setdefault(
            bet.user.username,
            {
                "username": bet.user.username,
                "points": 0,
                "order": 0,
            },
        )
        user_result_map_total.setdefault(
            bet.user.username,
            {
                "username": bet.user.username,
                "points": 0,
                "order": 0,
            },
        )
        if bet.type in ("SEASON_DRIVER", "SEASON_TEAM"):
            user_result_map_season[bet.user.username]["points"] += bet.result
            user_result_map_total[bet.user.username]["points"] += bet.result
            if bet.extra == "MATCH OK":
                user_result_map_season[bet.user.username]["points"] += 0.5
                user_result_map_total[bet.user.username]["points"] += 0.5

        else:
            user_result_map_races[bet.user.username]["points"] += bet.result
            user_result_map_total[bet.user.username]["points"] += bet.result

    user_result_races = sorted(
        user_result_map_races.values(), key=lambda item: item["points"], reverse=True
    )
    user_result_season = sorted(
        user_result_map_season.values(), key=lambda item: item["points"], reverse=True
    )
    user_result_total = sorted(
        user_result_map_total.values(), key=lambda item: item["points"], reverse=True
    )

    return render_template(
        "current_top_players.html",
        data={
            "RACES": user_result_races,
            "SEASON": user_result_season,
            "TOTAL": user_result_total,
        },
    )

    sums_for_users = defaultdict(float)  # map user: points
    for bet, user in bet_user:
        race_result = race_result_map.get(bet.race_id) or None
        if race_result and bet:
            _, points = evaluate_result_for_user(race_result, bet)
        else:
            points = 0.0
        sums_for_users[user.username] += points
        total[user.username] += points

    for username in sums_for_users:
        current_points = sums_for_users[username]
        out.append({"user": username, "points": current_points})
        # poresit pak stejne pozice?
    users = db.session.query(User).all()
    season_results = compute_season_result(users)

    season_out = []
    for user in users:
        points = season_results[user.username]["total"]
        season_out.append({"points": points, "user": user.username})
        total[user.username] += points
    full_out = []

    for username, points in total.items():
        full_out.append({"points": points, "user": username})
    # import pdb; pdb.set_trace()
    data = {}
    data["RACE"] = sorted(out, key=lambda d: d["points"], reverse=True)
    data["SEASON"] = sorted(season_out, key=lambda d: d["points"], reverse=True)
    data["FULL"] = sorted(full_out, key=lambda d: d["points"], reverse=True)

    return render_template(
        "current_top_players.html",
        data=data,
    )


# guess_overview/season/load
@main.route("/guess_overview/season/load")
@login_required
def update_standings():
    with Client("https://api.jolpi.ca/") as client:
        driver_standings = get_drivers_standings(client)
        sleep(5)
        constructor_standings = get_constructors_standings(client)
        for driver_id, item in driver_standings.items():
            stmt = (
                update(Competitor)
                .where(Competitor.ext_id == driver_id)
                .values(points=item["points"], position=item["position"])
            )
            _db_exec(stmt)
        for constructor_id, item in constructor_standings.items():
            stmt = (
                update(Competitor)
                .where(Competitor.ext_id == constructor_id)
                .values(points=item["points"], position=item["position"])
            )
            _db_exec(stmt)
        db.session.commit()

    return {"status": "standings updated"}


@main.route("/compute_season")
@login_required
def compute_season_route():
    # import pdb; pdb.set_trace()
    stmt = select(User)
    users = _db_exec(stmt).scalars().all()

    adjusted_drivers_standings = get_driver_adjusted_standings()
    constructors_standings_map = get_constr_standings()

    for user in users:
        compute_driver_season(user, adjusted_drivers_standings)
        compute_constr_result(user, constructors_standings_map)
        compute_team_match_result(user, adjusted_drivers_standings)
    db.session.commit()
    return {"status": "season computed"}


def get_driver_adjusted_standings():
    stmt = (
        select(Competitor)
        .where(Competitor.type == "DRIVER")
        .order_by(Competitor.position)
    )  # sort by  position ascending
    drivers_standings = _db_exec(stmt).scalars().all()
    adjusted_drivers_standings = {}
    pos = 1
    for item in drivers_standings:
        if item.code == "COL":
            continue
        adjusted_drivers_standings[item.code] = {
            "points": item.points,
            "position": pos,
            "ext_id": item.ext_id,
            "code": item.code,
        }
        pos += 1
    return adjusted_drivers_standings


def get_constr_standings():
    stmt = (
        select(Competitor)
        .where(Competitor.type == "TEAM")
        .order_by(Competitor.position)
    )  # sort by  position ascending
    constructors_standings = _db_exec(stmt).scalars().all()
    constructors_standings_map = {item.ext_id: item for item in constructors_standings}
    return constructors_standings_map

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

from .results import (
    evaluate_result_for_user,
    get_constructors_standings,
    get_drivers_standings,
    get_result_for_round,
    make_results_map,
    season_result,
    team_drivers_map,
    team_match_results,
)
from .utils import (
    date_or_none,
    get_current_race,
    get_label_attr_season,
    get_locks_race,
    is_bet_locked,
    lock_or_value,
)

MESSAGES = {
    "BET_SAVED": "Tip v pořádku uložen",
}
SUNDAY_TYPES = ("RACE", "SC", "FASTEST", "BONUS", "DRIVERDAY")

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


main = Blueprint("main", __name__)


@main.route("/health")
def health():
    return {"status": "OK"}


@main.route("/")
def index():
    return render_template("index.html")


def _db_exec(stmt):
    return db.session.execute(stmt)


### not used - maybe improve?
@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", name=current_user.username)


def _get_current_race():
    stmt = db.select(Race)
    races = _db_exec(stmt).scalars().all()
    return get_current_race(races)


@main.route("/race")
@login_required
def race_current():
    race = _get_current_race()
    return redirect(url_for(".race", external_circuit_id=race.ext_id))


@main.route("/race/<string:external_circuit_id>", methods=["GET", "POST"])
@login_required
def race(external_circuit_id):
    ##TODO create default bets foa all users/races
    stmt = db.select(Competitor).where(
        Competitor.type == "DRIVER", Competitor.active == True
    )
    res = _db_exec(stmt)
    drivers_codes = [driver.code for driver in res.scalars()]

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
    currrent_race = get_current_race(races)
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
    return render_template("wip.html")
    locked = bool(os.getenv("SEASON_LOCK", ""))

    data = {}

    drivers = [
        driver.serialize()
        for driver in db.session.query(Driver).all()
        if driver.code not in ("DRU", "BEA")  # to change to driver.season_active
    ]
    teams = [constr.serialize() for constr in db.session.query(Constructor).all()]
    assert len(drivers) == 20
    assert len(teams) == 10

    bets_for_user = [
        bet
        for bet in (
            db.session.query(SeasonBet)
            .filter(SeasonBet.user_id == current_user.id)
            .all()
        )
    ]

    bets_in_dict = {}
    for item in bets_for_user:
        bets_in_dict.setdefault(item.type, {})[item.rank] = item

    # show, update
    if request.method == "POST":
        commit_change = False
        for type in ("DRIVER", "TEAM"):
            for rank in range(1, 21):
                val = request.form.get(f"select_{type.lower()}_{rank}") or None

                bet_for_rank = bets_in_dict.get(type, {}).get(rank) or None
                if val is None and bet_for_rank is None:
                    # no bet from web form + nothing to update
                    continue

                if bet_for_rank:
                    # update
                    bet_for_rank.value = val
                    commit_change = True

                else:
                    # create new

                    new_bet = SeasonBet.from_data(
                        type=type,
                        data={
                            "value": val,
                            "rank": rank,
                            "user_id": current_user.id,
                        },
                    )
                    db.session.add(new_bet)
                    commit_change = True

        if commit_change:
            db.session.commit()
            flash("Tip v pořádku uložen")

        return redirect(url_for("main.season"))

    data = {
        "bet": SeasonBet.serialize(bets_for_user),
        "drivers": drivers,
        "teams": teams,
        "locked": locked,
    }

    return render_template(
        "season.html",
        data=data,
    )


@main.route("/season", methods=["POST"])
@login_required
def season_post():
    return render_template("wip.html")
    lock = False
    if os.getenv("SEASON_LOCK", ""):
        lock = True

    data = {}

    drivers = [
        driver.code for driver in db.session.query(Driver).all() if driver.code != "DRU"
    ]
    constructors = [constr.code for constr in db.session.query(Constructor).all()]
    label_attrs_lists = get_label_attr_season()

    data["drivers"] = label_attrs_lists[0]
    data["constructors"] = label_attrs_lists[1]

    season_guess = (
        db.session.query(SeasonGuess)
        .filter(SeasonGuess.user_id == current_user.id)
        .first()
    )
    if not lock:
        if season_guess:
            # update
            for item in data["constructors"]:
                setattr(season_guess, item["attr"], request.form.get(item["attr"]))
            for item in data["drivers"]:
                setattr(season_guess, item["attr"], request.form.get(item["attr"]))
            db.session.commit()
        else:
            new_season_guess = SeasonGuess(user_id=current_user.id)
            for item in data["constructors"]:
                setattr(new_season_guess, item["attr"], request.form.get(item["attr"]))
            for item in data["drivers"]:
                setattr(new_season_guess, item["attr"], request.form.get(item["attr"]))

            db.session.add(new_season_guess)
            db.session.commit()
            season_guess = new_season_guess

        flash("Tip v pořádku uložen")

    return render_template(
        "season.html",
        data=data,
        guess=season_guess,
        drivers=drivers,
        lock=lock,
        constructors=constructors,
    )


@main.route("/bet_result")
@login_required
def bet_result_current():
    race = _get_current_race()
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


@main.route("/bet_overview")
@login_required
def bet_overview():
    return render_template("wip.html")
    stmt = select(Race)
    races = _db_exec(stmt).scalars().all()

    stmt = select(User)
    users = _db_exec(stmt).scalars().all()

    data = []

    for race in sorted(races, key=lambda x: x.race_date):

        thead, rows = get_rows_race_overview(race, users, current_user.id)

        data.append({"thead": thead, "rows": rows})

    return render_template("guess_overview_race.html", data=data)


def get_result(result, attr):
    return getattr(result, attr) if result else "-"


def get_rows_race_overview(race, users, current_user_id):
    stmt = select(RaceResult).where(RaceResult.race_id == race.id)
    # result = db.session.query(RaceResult).filter(RaceResult.race_id == race.id).first()
    res = _db_exec(stmt).scalars().all()

    thead = [
        "Tip",
        "Výsledek",
    ]
    quali_result = get_result(result, "quali")
    quali_row = ["Vítěz kvalifikace", quali_result]

    if race.sprint_date:
        sprint_result = get_result(result, "sprint")

        sprint_row = ["Vítěz sprintu", sprint_result]

    _1_row = ["Vítěz závodu", get_result(result, "first")]
    _2_row = ["Druhé místo", get_result(result, "second")]
    _3_row = ["Třetí místo", get_result(result, "third")]

    fastest_lap_row = ["Nejrychlejší kolo", get_result(result, "fastest_lap")]
    safety_car_row = ["Výjezd safety car", get_result(result, "safety_car")]
    bonus_row = ["Bonusový tip", get_result(result, "bonus")]

    keys = [
        "quali",
        "first",
        "second",
        "third",
        "fastest_lap",
        "safety_car",
        "bonus",
    ]
    if race.sprint_date:
        keys.insert(0, "sprint")

    rows = [
        quali_row,
        _1_row,
        _2_row,
        _3_row,
        fastest_lap_row,
        safety_car_row,
        bonus_row,
    ]

    if race.sprint_date:
        rows.insert(0, sprint_row)

    row_map = {key: row for key, row in zip(keys, rows)}
    race_id = race.id
    thead[0] = race.name.replace("Grand Prix", "GP")
    locks = get_locks_race(race)

    for user in sorted(users, key=lambda x: x.username):
        guess = (
            db.session.query(RaceGuess)
            .filter(RaceGuess.user_id == user.id)
            .filter(RaceGuess.race_id == race_id)
            .first()
        )

        if guess is None:
            guess_set = False
            result_for_user = None
            thead.extend([user.username, "-"])
        else:
            if result:
                result_for_user, points_sum = evaluate_result_for_user(result, guess)
                thead.extend([user.username, points_sum])
            else:
                result_for_user = None
                thead.extend([user.username, "-"])
            guess_set = True

        for attr, row in row_map.items():
            if not race.sprint_date and attr == "sprint":
                continue
            value = get_attr_value(
                guess_set,
                guess,
                attr,
                is_attr_locked(locks, attr),
                current_user_id,
                user,
            )

            points = result_for_user[attr] if result_for_user else "-"

            row.extend([value, points])
    return thead, rows


@main.route("/top_players")
@login_required
def top_players():
    return render_template("wip.html")
    total = defaultdict(float)
    out = []
    bet_user = db.session.query(RaceGuess, User).join(User).all()
    race_result_map = {
        race.id: result
        for race, result in db.session.query(Race, RaceResult).join(RaceResult).all()
    }

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


@main.route("/guess_overview/season")
@login_required
def guess_overview_season():
    return render_template("wip.html")
    # results_available = bool(os.getenv("SEASON_RESULTS", ""))
    # if not results_available:
    #    return render_template("wip.html")

    result = db.session.query(SeasonBet, User).join(User).all()
    data = {
        "DRIVER": {},
        "TEAM": {},
    }
    users = db.session.query(User).all()
    stgds = db.session.query(Standings).all()
    season_results = compute_season_result(users)

    for type in ("DRIVER", "TEAM"):
        for bet, user in result:
            if bet.type == type:
                value = bet.value
                data[type].setdefault(user.username, {}).setdefault(bet.rank, {})[
                    "bet"
                ] = value
                points = (
                    season_results[user.username]["data"][type.lower() + "s"]
                    .get(bet.rank, {})
                    .get("points", 0)
                )
                data[type].setdefault(user.username, {}).setdefault(bet.rank, {})[
                    "points"
                ] = points

    stgds_drivers = {
        int(item.position): item.name for item in stgds if item.type == "DRIVER"
    }

    stgds_teams = {
        int(item.position): item.name for item in stgds if item.type == "TEAM"
    }

    stgds_team_match = {}
    data["TEAM_MATCH"] = {}
    for team in sorted(list(team_drivers_map.keys())):
        better_worse = get_team_match_stdg_result(season_results, team)
        stgds_team_match[team] = better_worse

        for user in season_results.keys():
            user_bet = season_results[user]["data"]["team_match"].get(team, {})
            if not user_bet:
                continue

            else:
                points = user_bet["points"]
            data["TEAM_MATCH"].setdefault(user, {}).setdefault(team, {})[
                "points"
            ] = points
            better = "n/a"
            worse = "n/a"
            for driver, res in user_bet.get("bet", {}).items():
                if res == True:
                    better = driver
                if res == False:
                    worse = driver

            data["TEAM_MATCH"].setdefault(user, {}).setdefault(team, {})[
                "bet"
            ] = f"{better} > {worse}"

    data["SUMS"] = {
        "DRIVER": {},
        "TEAM": {},
        "TEAM_MATCH": {},
    }  ### SUMS.DRIVERS[username] = points
    for user in users:
        for type in ("DRIVER", "TEAM", "TEAM_MATCH"):
            data["SUMS"][type][user.username] = _get_sum_user(
                data[type].get(user.username, {})
            )

    data["DRIVER_RESULT"] = stgds_drivers
    data["TEAM_RESULT"] = stgds_teams
    data["TEAM_MATCH_RESULT"] = stgds_team_match

    return render_template("guess_overview_season.html", data=data)


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


@main.route("/result/<string:external_circuit_id>/evaluate", methods=["GET"])
@login_required
def evaluate_result(external_circuit_id):
    if current_user.role != "ADMIN":
        raise Exception

    race = (
        db.session.query(Race)
        .filter(Race.external_circuit_id == external_circuit_id)
        .first()
    )
    race_id = race.id
    bonus_question = (
        db.session.query(BonusGuess).filter(BonusGuess.race_id == race_id).first().text
    )
    bonus_answer = (
        db.session.query(RaceResult).filter(RaceResult.race_id == race_id).first().bonus
    )
    bonus_table = [bonus_question, bonus_answer]

    guesses = db.session.query(RaceGuess).filter(RaceGuess.race_id == race_id)
    thead = ["USERNAME", "BONUSGUESS"]
    rows = []
    for guess in guesses:
        bonus_guess = guess.bonus
        user = db.session.query(User).filter(User.id == guess.user_id).first()

        rows.append([user.username, bonus_guess, user.id])

    return render_template(
        "evaluate.html", race=race, thead=thead, rows=rows, bonus_table=bonus_table
    )


@main.route("/result/<string:external_circuit_id>/evaluate", methods=["POST"])
@login_required
def evaluate_result_post(external_circuit_id):
    if current_user.role != "ADMIN":
        raise Exception
    race = (
        db.session.query(Race)
        .filter(Race.external_circuit_id == external_circuit_id)
        .first()
    )
    race_id = race.id
    bonus_question = (
        db.session.query(BonusGuess).filter(BonusGuess.race_id == race_id).first().text
    )
    bonus_answer = (
        db.session.query(RaceResult).filter(RaceResult.race_id == race_id).first().bonus
    )
    bonus_table = [bonus_question, bonus_answer]

    guesses = db.session.query(RaceGuess).filter(RaceGuess.race_id == race_id)
    thead = ["USERNAME", "BONUSGUESS"]
    rows = []
    for guess in guesses:
        bonus_guess = guess.bonus
        user = db.session.query(User).filter(User.id == guess.user_id).first()

        rows.append([user.username, bonus_guess, user.id])

    users = db.session.query(User).all()
    for user in users:
        bonus_ok = True if request.form.get(str(user.id), "") == "on" else False
        race_guess = (
            db.session.query(RaceGuess)
            .filter(RaceGuess.user_id == user.id)
            .filter(RaceGuess.race_id == race_id)
            .first()
        )
        if race_guess:
            race_guess.bonus_ok = bonus_ok
            db.session.commit()

    return render_template(
        "evaluate.html", race=race, thead=thead, rows=rows, bonus_table=bonus_table
    )


@main.route("/result/<string:external_circuit_id>", methods=["GET"])
@login_required
def load_results(external_circuit_id):
    if current_user.role != "ADMIN":
        raise Exception

    race = (
        db.session.query(Race)
        .filter(Race.external_circuit_id == external_circuit_id)
        .first()
    )

    result = db.session.query(RaceResult).filter(RaceResult.race_id == race.id).first()
    loaded = False
    if result:
        loaded = True
        flash("ALREADY LOADED")
    else:
        flash(f"RESULT FOR {external_circuit_id} NOT LOADED!")
    return render_template("result.html", race=race, loaded=loaded)


@main.route("/result/<string:external_circuit_id>", methods=["POST"])
@login_required
def load_results_post(external_circuit_id):
    if current_user.role != "ADMIN":
        raise Exception

    race = (
        db.session.query(Race)
        .filter(Race.external_circuit_id == external_circuit_id)
        .first()
    )

    result = db.session.query(RaceResult).filter(RaceResult.race_id == race.id).first()
    loaded = False
    if result:
        loaded = True
        flash("ALREADY LOADED")
    else:
        result_data = get_result_for_round(
            race.round, True if race.sprint_date else False
        )

        safety_car_result = request.form.get("safety_car")
        bonus_result = request.form.get("bonus")

        result = RaceResult(
            quali=result_data["quali"],
            sprint=result_data["sprint"],
            first=result_data["first"],
            second=result_data["second"],
            third=result_data["third"],
            fastest_lap=result_data["fastest_lap"],
            safety_car=safety_car_result,
            bonus=bonus_result,
            race_id=race.id,
        )
        db.session.add(result)
        db.session.commit()
        flash("RESULT SAVED TO DB")

    return render_template("result.html", race=race, loaded=loaded)


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


def load_standings():
    drivers_stdgs = get_drivers_standings()
    sleep(5)
    team_stdgs = get_constructors_standings()
    out = "ERROR"
    _types = ("DRIVER", "TEAM")
    for _type, stgds in zip(_types, [drivers_stdgs, team_stdgs]):
        for item in stgds:
            db_item = (
                db.session.query(Standings)
                .filter(Standings.type == _type)
                .filter(Standings.name == item[_type.lower()])
                .first()
            )

            if db_item is None:
                # create new
                new_item = Standings(
                    position=item["position"],
                    type=_type,
                    name=item[_type.lower()],
                    points=item["points"],
                )
                db.session.add(new_item)
                db.session.commit()
                out = "NEW"

            else:
                db_item.position = item["position"]
                db_item.name = item[_type.lower()]
                db_item.points = item["points"]
                db.session.commit()
                out = "UPDATE"
                # update
    return out


def compute_season_result(users):
    stdgs = db.session.query(Standings).all()

    drivers = [item for item in stdgs if item.type == "DRIVER"]
    teams = [item for item in stdgs if item.type == "TEAM"]

    drivers_map = make_results_map(drivers)
    teams_map = make_results_map(teams)

    out = {}
    for user in users:
        bets_for_user = [
            bet
            for bet in (
                db.session.query(SeasonBet).filter(SeasonBet.user_id == user.id).all()
            )
        ]

        bet = SeasonBet.serialize(bets_for_user)
        season_drivers_for_user = season_result(
            bet["DRIVER"], drivers_map, std_type="DRIVERS"
        )
        season_teams_for_user = season_result(bet["TEAM"], teams_map, std_type="TEAMS")

        team_match_for_user = team_match_results(bet["DRIVER"], drivers)

        # total points per user
        # import pdb; pdb.set_trace()
        total_points = get_points_for_user(
            season_drivers_for_user,
            season_teams_for_user,
            team_match_for_user,
        )

        # import pdb;pdb.set_trace()

        out[user.username] = {
            "total": total_points,
            "data": {
                "drivers": season_drivers_for_user,
                "teams": season_teams_for_user,
                "team_match": team_match_for_user,
            },
        }
    # import pdb; pdb.set_trace()
    # detailed points per user
    return out


def get_points_for_user(*dicts):
    out = 0
    for data in dicts:
        for item in data.values():
            out += item["points"]

    return out

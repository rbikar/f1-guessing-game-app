import os
from collections import OrderedDict

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import (
    BonusGuess,
    Constructor,
    Driver,
    Race,
    RaceGuess,
    RaceResult,
    SeasonGuess,
    User,
)

from .results import evaluate_result_for_user, get_result_for_round
from .utils import (
    date_or_none,
    get_current_race,
    get_label_attr_season,
    get_locks_race,
    is_attr_locked,
)

main = Blueprint("main", __name__)


@main.route("/health")
def health():
    return {"status": "OK"}


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", name=current_user.username)


@main.route("/race")
@login_required
def race_current():
    races = db.session.query(Race).all()
    race = get_current_race(races)
    return redirect(url_for(".race", short_name=race.short_name))


@main.route("/race/<string:short_name>")
@login_required
def race(short_name):
    drivers = [driver.code for driver in db.session.query(Driver).all()]
    race = db.session.query(Race).filter(Race.short_name == short_name).first()

    guess = (
        db.session.query(RaceGuess)
        .filter(RaceGuess.race_id == race.id)
        .filter(RaceGuess.user_id == current_user.id)
        .first()
    )
    bonus = db.session.query(BonusGuess).filter(BonusGuess.race_id == race.id).first()
    locks = get_locks_race(race)
    start_times = {
        "q_start": date_or_none(race.quali_start),
        "s_start": date_or_none(race.sprint_start) if race.type == "SPRINT" else None,
        "r_start": date_or_none(race.race_start),
    }
    return render_template(
        "race.html",
        drivers=drivers,
        guess=guess,
        locks=locks,
        race=race,
        race_type=race.type,
        start_times=start_times,
        bonus=bonus,
    )


@main.route("/race/<string:short_name>", methods=["POST"])
@login_required
def race_post(short_name):
    current_race_short_name = short_name
    drivers = [driver.code for driver in db.session.query(Driver).all()]

    keys = [
        "quali",
        "sprint",
        "first",
        "second",
        "third",
        "safety_car",
        "fastest_lap",
        "bonus",
    ]
    form_data = {}
    for key in keys:
        form_data[key] = request.form.get(key)

    race = (
        db.session.query(Race)
        .filter(Race.short_name == current_race_short_name)
        .first()
    )
    locks = get_locks_race(race)

    guess = (
        db.session.query(RaceGuess)
        .filter(RaceGuess.race_id == race.id)
        .filter(RaceGuess.user_id == current_user.id)
        .first()
    )

    bonus = db.session.query(BonusGuess).filter(BonusGuess.race_id == race.id).first()
    if guess:
        ### update
        for attr, value in form_data.items():
            if is_attr_locked(locks, attr):
                continue
            setattr(guess, attr, value)
        db.session.commit()
    else:
        ### create new guess
        new_guess = RaceGuess(
            race_id=db.session.query(Race)
            .filter(Race.short_name == current_race_short_name)
            .first()
            .id,
            user_id=current_user.id,
        )
        for attr, value in form_data.items():
            if is_attr_locked(locks, attr):
                continue
            setattr(new_guess, attr, value)

        db.session.add(new_guess)
        db.session.commit()
        guess = new_guess

    flash("Tip v pořádku uložen")
    start_times = {
        "q_start": date_or_none(race.quali_start),
        "s_start": date_or_none(race.sprint_start) if race.type == "SPRINT" else None,
        "r_start": date_or_none(race.race_start),
    }
    return render_template(
        "race.html",
        drivers=drivers,
        guess=guess,
        locks=locks,
        race=race,
        race_type=race.type,
        bonus=bonus,
        start_times=start_times,
    )


@main.route("/races", methods=["GET"])
@login_required
def races():
    def get_row(race):
        return {
            "name": race.name.replace("Grand Prix", "GP"),
            "q": date_or_none(race.quali_start),
            "s": date_or_none(race.sprint_start) if race.type == "SPRINT" else "-----",
            "r": date_or_none(race.race_start),
            "short_name": race.short_name,
        }

    races = db.session.query(Race).all()
    currrent_race = get_current_race(races)
    table_head = ["F1 2022", "Q", "SPRINT", "ZÁVOD"]
    finished = []
    current = []
    upcoming = []
    switch = False
    rows = {}
    for race in sorted(races, key=lambda x: x.race_start):
        if race.short_name == currrent_race.short_name:
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


@main.route("/season", methods=["GET"])
@login_required
def season():
    lock = False
    if os.getenv("SEASON_LOCK", ""):
        lock = True
    data = {}

    drivers = [
        driver.code for driver in db.session.query(Driver).all() if driver.code != "HUL"
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

    if os.getenv("WIP", ""):
        return render_template("wip.html")
    return render_template(
        "season.html",
        data=data,
        guess=season_guess,
        drivers=drivers,
        constructors=constructors,
        lock=lock,
    )


@main.route("/season", methods=["POST"])
@login_required
def season_post():
    lock = False
    if os.getenv("SEASON_LOCK", ""):
        lock = True

    data = {}

    drivers = [
        driver.code for driver in db.session.query(Driver).all() if driver.code != "HUL"
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


@main.route("/guess_overview")
@login_required
def guess_overview():
    if os.getenv("WIP", "1"):
        return render_template("wip.html")
    data = {}
    users = db.session.query(User).all()
    all_races = db.session.query(Race).all()
    race = get_current_race(all_races)
    table_head = [race.name, "Kvalifikace", "Vitez sprintu", "Vitez zavodu"]

    rows = []
    for user in sorted(users, key=lambda x: x.username):
        guess = (
            db.session.query(RaceGuess)
            .filter(RaceGuess.id == user.id)
            .filter(RaceGuess.race_id == race.id)
            .first()
        )

        if guess:
            row = [user.username, guess.quali]
            rows.append(row)

    return render_template(
        "guess_overview.html", data=data, table_head=table_head, rows=rows
    )


@main.route("/guess_overview/race")
@login_required
def guess_overview_race():
    races = db.session.query(Race).all()
    users = db.session.query(User).all()
    current_user_id = current_user.id

    data = []

    for race in sorted(races, key=lambda x: x.race_start):
        thead, rows = get_rows_race_overview(race, users, current_user_id)
        data.append({"thead": thead, "rows": rows})
    return render_template("guess_overview_race.html", data=data)


def get_result(result, attr):
    return getattr(result, attr) if result else "-"


def get_rows_race_overview(race, users, current_user_id):
    result = db.session.query(RaceResult).filter(RaceResult.race_id == race.id).first()

    thead = [
        "Tip",
        "Výsledek",
    ]
    quali_result = get_result(result, "quali")
    quali_row = ["Vítěz kvalifikace", quali_result]

    if race.type == "SPRINT":
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
    if race.type == "SPRINT":
        keys.insert(1, "sprint")

    rows = [
        quali_row,
        _1_row,
        _2_row,
        _3_row,
        fastest_lap_row,
        safety_car_row,
        bonus_row,
    ]

    if race.type == "SPRINT":
        rows.insert(1, sprint_row)

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
            if race.type != "SPRINT" and attr == "sprint":
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
    users = db.session.query(User).all()
    races = db.session.query(Race).all()
    thead = ["Pořadí", "Hráč", "Body"]

    rows = []
    sums_for_users = []

    for user in users:
        sum_for_user = 0.0
        for race in races:
            result_for_race = (
                db.session.query(RaceResult)
                .filter(RaceResult.race_id == race.id)
                .first()
            )
            guess = (
                db.session.query(RaceGuess)
                .filter(RaceGuess.user_id == user.id)
                .filter(RaceGuess.race_id == race.id)
                .first()
            )
            if not result_for_race or not guess:
                points_sum = 0.0
            else:
                _, points_sum = evaluate_result_for_user(result_for_race, guess)
            sum_for_user += points_sum

        sums_for_users.append(
            (
                user.username,
                sum_for_user,
            )
        )

    for order, result in zip(
        range(1, len(users) + 1),
        sorted(sums_for_users, key=lambda x: x[1], reverse=True),
    ):
        row = [f"{order}.", result[0], result[1]]
        rows.append(row)

    return render_template("current_top_players.html", thead=thead, rows=rows)


@main.route("/guess_overview/season")
@login_required
def guess_overview_season():
    users = db.session.query(User).all()

    thead_drivers = [
        "Jezdci",
        "Výsledek",
    ]

    rows_drivers = []
    for user in sorted(users, key=lambda x: x.username):
        thead_drivers.append(user.username)

        result_driver = get_season_result_driver(user.username)
        thead_drivers.append(result_driver)

    guess_user_map = get_user_guess_map(users)
    for order in range(1, 21):
        label = "MISTR" if order == 1 else f"{order}."
        result_for_driver = "-"  # TODO get result from data
        row = [label, result_for_driver]
        row.extend(season_row_driver(order, guess_user_map))
        rows_drivers.append(row)

    thead_constr = [
        "Týmy",
        "Výsledek",
    ]

    rows_constr = []
    for user in sorted(users, key=lambda x: x.username):
        thead_constr.append(user.username)

        result_driver = get_season_result_constr(user.username)
        thead_constr.append(result_driver)

    for order in range(1, 11):
        label = "MISTR" if order == 1 else f"{order}."
        result_for_constr = "-"  # TODO get result from data
        row = [label, result_for_constr]
        row.extend(season_row_constr(order, guess_user_map))
        rows_constr.append(row)

    return render_template(
        "guess_overview_season.html",
        thead_drivers=thead_drivers,
        rows_drivers=rows_drivers,
        thead_constr=thead_constr,
        rows_constr=rows_constr,
    )


def season_row_driver(order, user_guess_map):
    row = []
    attr = f"_{order}d"
    for user, guess in user_guess_map.items():
        if guess:
            value = getattr(guess, attr)
        else:
            value = None

        points = "-"  # TODO add point counting
        row.append(value if value else "N")
        row.append(f"{points}")

    return row


def season_row_constr(order, user_guess_map):
    row = []
    attr = f"_{order}c"
    for user, guess in user_guess_map.items():
        if guess:
            value = getattr(guess, attr)
        else:
            value = None

        points = "-"  # TODO add point counting
        row.append(value if value else "N")
        row.append(f"{points}")

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


def get_season_result_driver(username):
    drivers = "-"
    return drivers


def get_season_result_constr(username):
    constructors = "-"
    return constructors


@main.route("/rules")
@login_required
def rules():
    return render_template("rules.html")


#### admin only / TODO move to different router


@main.route("/result/<string:short_name>/evaluate", methods=["GET"])
@login_required
def evaluate_result(short_name):
    if current_user.role != "ADMIN":
        raise Exception

    race = db.session.query(Race).filter(Race.short_name == short_name).first()
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


@main.route("/result/<string:short_name>/evaluate", methods=["POST"])
@login_required
def evaluate_result_post(short_name):
    if current_user.role != "ADMIN":
        raise Exception
    race = db.session.query(Race).filter(Race.short_name == short_name).first()
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
        bonus_ok = True if request.form.get(user.id) else False
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


@main.route("/result/<string:short_name>", methods=["GET"])
@login_required
def load_results(short_name):
    if current_user.role != "ADMIN":
        raise Exception

    race = db.session.query(Race).filter(Race.short_name == short_name).first()

    result = db.session.query(RaceResult).filter(RaceResult.race_id == race.id).first()
    loaded = False
    if result:
        loaded = True
        flash("ALREADY LOADED")

    return render_template("result.html", race=race, loaded=loaded)


@main.route("/result/<string:short_name>", methods=["POST"])
@login_required
def load_results_post(short_name):
    if current_user.role != "ADMIN":
        raise Exception

    race = db.session.query(Race).filter(Race.short_name == short_name).first()

    result = db.session.query(RaceResult).filter(RaceResult.race_id == race.id).first()
    loaded = False
    if result:
        loaded = True
        flash("ALREADY LOADED")
    else:
        result_data = get_result_for_round(
            race.round, True if race.type == "SPRINT" else False
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


@main.route("/results/", methods=["GET"])
@login_required
def results_table():
    if current_user.role != "ADMIN":
        raise Exception
    races = db.session.query(Race).all()

    def get_row(race):
        return {
            "name": race.name.replace("Grand Prix", "GP"),
            "short_name": race.short_name,
        }

    rows = []
    for race in races:
        row = get_row(race)
        rows.append(row)

    return render_template("results_table.html", rows=rows)

import os

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import (
    BonusGuess,
    Constructor,
    Driver,
    Race,
    RaceGuess,
    SeasonGuess,
    User,
)

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

    drivers = [driver.code for driver in db.session.query(Driver).all()]
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

    drivers = [driver.code for driver in db.session.query(Driver).all()]
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
    if os.getenv("WIP", ""):
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

    print(rows)
    return render_template(
        "guess_overview.html", data=data, table_head=table_head, rows=rows
    )


@main.route("/guess_overview/race")
@login_required
def guess_overview_race():
    return render_template("wip.html")


@main.route("/guess_overview/season")
@login_required
def guess_overview_season():
    return render_template("wip.html")

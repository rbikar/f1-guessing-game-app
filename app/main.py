import os

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import BonusGuess, Constructor, Driver, Race, RaceGuess, User

from .utils import (
    date_or_none,
    get_current_race,
    get_locks_race,
    is_attr_locked,
    validate_season,
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

    locks = get_locks_race(race)

    return render_template(
        "race.html",
        drivers=drivers,
        guess=guess,
        locks=locks,
        race=race,
        race_type=race.type,
    )


@main.route("/race/<string:short_name>", methods=["POST"])
@login_required
def race_post(short_name):
    ### updae do db
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
    return render_template(
        "race.html",
        drivers=drivers,
        guess=guess,
        locks=locks,
        race=race,
        race_type=race.type,
        bonus=bonus,
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


@main.route("/season")
@login_required
def season():
    lock = False
    if os.getenv("SEASON_LOCK", ""):
        lock = True
    data = {}
    drivers = [driver.code for driver in db.session.query(Driver).all()]
    constructors = [constr.code for constr in db.session.query(Constructor).all()]
    lock = False
    if os.getenv("WIP", ""):
        return render_template("wip.html")
    return render_template(
        "season.html", data=data, guess=data, drivers=drivers, lock=lock
    )


@main.route("/season/", methods=["POST"])
@login_required
def season_post():
    lock = False
    if os.getenv("SEASON_LOCK", ""):
        lock = True

    data = {}
    if validate_season(request.form):
        ### ulozit do db
        pass
    else:
        flash("TIPY ZADANE ZLE")
        ### neulozit a vratit do fomru co tam zadal
    drivers = [driver.code for driver in db.session.query(Driver).all()]
    constructors = [constr.code for constr in db.session.query(Constructor).all()]

    return render_template(
        "season.html", data=data, guess=data, drivers=drivers, lock=lock
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

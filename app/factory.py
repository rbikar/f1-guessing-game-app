import json
import os
from datetime import datetime, timedelta

from flask import Flask, session
from flask_login import LoginManager

import app.models
from app import db


def create_app(db_uri=None):
    flask_app = Flask(__name__)
    config = {}
    flask_app.config["SECRET_KEY"] = os.getenv("DB_KEY", "!!!SET-THIS!!!")
    test = os.getenv("F1TEST", "")
    if not test:
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = db_uri or get_db_url(config)
    else:
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.sqlite3"

    db.init_app(flask_app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(flask_app)

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return app.models.User.query.get(int(user_id))

    @flask_app.before_request
    def make_session_permanent():
        session.permanent = True
        flask_app.permanent_session_lifetime = timedelta(minutes=30)

    # blueprint for auth routes in our app
    from app.auth import auth as auth_blueprint

    flask_app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint

    flask_app.register_blueprint(main_blueprint)

    return flask_app


def get_db_url(config):
    PGHOST = os.getenv("PGHOST") or config.get("PGHOST")
    PGUSER = os.getenv("PGUSER") or config.get("PGUSER")
    PGPASSWORD = os.getenv("PGPASSWORD") or config.get("PGPASSWORD")
    PGPORT = os.getenv("PGPORT") or config.get("PGPORT")
    PGDATABASE = os.getenv("PGDATABASE") or config.get("PGDATABASE")

    return f"postgresql+psycopg2://{ PGUSER }:{ PGPASSWORD }@{ PGHOST }:{ PGPORT }/{ PGDATABASE }"


def load_races_to_db():
    with open("app/data/races.json", "r") as f:
        races = json.load(f)
        for race in races:
            race_obj = (
                db.session.query(app.models.Race)
                .filter(app.models.Race.short_name == race["short_name"])
                .first()
            )
            if race_obj:
                if not os.getenv("UPDATE_RACES", ""):
                    return

                race_obj.short_name = race["short_name"]
                race_obj.type = race["type"]
                race_obj.round = race["round"]
                race_obj.quali_start = (
                    None
                    if "TBC" == race["quali_start"]
                    else datetime.fromisoformat(race["quali_start"])
                )
                race_obj.sprint_start = (
                    None
                    if "TBC" == race["sprint_start"]
                    else datetime.fromisoformat(race["sprint_start"])
                )
                race_obj.race_start = (
                    None
                    if "TBC" == race["race_start"]
                    else datetime.fromisoformat(race["race_start"])
                )
                race_obj.name = race["name"]

                db.session.commit()

            else:
                new_race = app.models.Race(
                    short_name=race["short_name"],
                    type=race["type"],
                    round=race["round"],
                    quali_start=None
                    if "TBC" == race["quali_start"]
                    else datetime.fromisoformat(race["quali_start"]),
                    sprint_start=None
                    if "TBC" == race["sprint_start"]
                    else datetime.fromisoformat(race["sprint_start"]),
                    race_start=None
                    if "TBC" == race["race_start"]
                    else datetime.fromisoformat(race["race_start"]),
                    name=race["name"],
                )

                db.session.add(new_race)
                db.session.commit()


def load_drivers_to_db():
    with open("app/data/drivers_codes.dat", "r") as f:
        for line in f:
            if line:
                line = line.strip()

                driver_obj = (
                    db.session.query(app.models.Driver)
                    .filter(app.models.Driver.code == line)
                    .first()
                )

                if driver_obj:
                    if not os.getenv("UPDATE_DRIVERS", ""):
                        return
                    # update
                    driver_obj.code = line
                    db.session.commit()
                else:
                    new_driver = app.models.Driver(code=line)
                    db.session.add(new_driver)
                    db.session.commit()


def load_constructors_to_db():
    with open("app/data/constructors_codes.dat", "r") as f:
        for line in f:
            if line:
                line = line.strip()

                constr_obj = (
                    db.session.query(app.models.Constructor)
                    .filter(app.models.Constructor.code == line)
                    .first()
                )

                if constr_obj:
                    if not os.getenv("UPDATE_CONSTRUCTORS", ""):
                        return
                    # update
                    constr_obj.code = line
                    db.session.commit()
                else:
                    new_constr = app.models.Constructor(code=line)
                    db.session.add(new_constr)
                    db.session.commit()


def load_empty_bonus_guesses_to_db():
    for race in db.session.query(app.models.Race).all():
        bonus = app.models.BonusGuess(
            race_id=race.id,
            text="",
            type=None,
        )
        db.session.add(bonus)
        db.session.commit()

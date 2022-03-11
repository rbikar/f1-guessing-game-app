from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    password = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)


class Race(db.Model):
    __tablename__ = "race"

    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(1000), unique=True)
    name = db.Column(db.String(1000), unique=True)
    quali_start = db.Column(db.TIMESTAMP(timezone=True))
    sprint_start = db.Column(db.TIMESTAMP(timezone=True))
    race_start = db.Column(db.TIMESTAMP(timezone=True))
    type = db.Column(db.String(1000))
    round = db.Column(db.String(1000))


####  vysledky do jine tabulky


class RaceGuess(db.Model):
    __tablename__ = "raceguess"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))

    quali = db.Column(db.String(1000))
    sprint = db.Column(db.String(1000))

    first = db.Column(db.String(1000))
    second = db.Column(db.String(1000))
    third = db.Column(db.String(1000))

    fastest_lap = db.Column(db.String(1000))
    safety_car = db.Column(db.Integer, default=12)
    bonus = db.Column(db.String(1000))


class SeasonGuess(db.Model):
    __tablename__ = "seasonguess"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    ###drivers
    winner = db.Column(db.String(1000))
    _2 = db.Column(db.String(1000))
    _3 = db.Column(db.String(1000))
    ### 20 jezdcu

    ###constructors
    #
    winner_constructor = db.Column(db.String(1000))
    ### 10 stsaji


class Driver(db.Model):
    __tablename__ = "driver"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy

    driver_id = db.Column(db.String(1000))
    number = db.Column(db.String(1000))
    code = db.Column(db.String(1000), unique=True)


class Constructor(db.Model):
    __tablename__ = "constructor"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy

    constructorId = db.Column(db.String(1000))
    name = db.Column(db.String(1000))
    code = db.Column(db.String(1000), unique=True)

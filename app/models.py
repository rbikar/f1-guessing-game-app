from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    password = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    role = db.Column(db.String(100))


class Race(db.Model):
    __tablename__ = "race"

    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100), unique=True)
    quali_start = db.Column(db.TIMESTAMP(timezone=True))
    sprint_start = db.Column(db.TIMESTAMP(timezone=True))
    race_start = db.Column(db.TIMESTAMP(timezone=True))
    type = db.Column(db.String(100))
    round = db.Column(db.String(100))


####  vysledky do jine tabulky


class RaceGuess(db.Model):
    __tablename__ = "raceguess"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))

    quali = db.Column(db.String(100))
    sprint = db.Column(db.String(100))

    first = db.Column(db.String(100))
    second = db.Column(db.String(100))
    third = db.Column(db.String(100))

    fastest_lap = db.Column(db.String(100))
    safety_car = db.Column(db.Integer)
    bonus = db.Column(db.String(100))


class SeasonGuess(db.Model):
    __tablename__ = "seasonguess"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    ###drivers
    _1d = db.Column(db.String(100))
    _2d = db.Column(db.String(100))
    _3d = db.Column(db.String(100))
    _4d = db.Column(db.String(100))
    _5d = db.Column(db.String(100))
    _6d = db.Column(db.String(100))
    _7d = db.Column(db.String(100))
    _8d = db.Column(db.String(100))
    _9d = db.Column(db.String(100))
    _10d = db.Column(db.String(100))
    _11d = db.Column(db.String(100))
    _12d = db.Column(db.String(100))
    _13d = db.Column(db.String(100))
    _14d = db.Column(db.String(100))
    _15d = db.Column(db.String(100))
    _16d = db.Column(db.String(100))
    _17d = db.Column(db.String(100))
    _18d = db.Column(db.String(100))
    _19d = db.Column(db.String(100))
    _20d = db.Column(db.String(100))
    ### 20 jezdcu

    ###constructors
    #
    _1c = db.Column(db.String(100))
    _2c = db.Column(db.String(100))
    _3c = db.Column(db.String(100))
    _4c = db.Column(db.String(100))
    _5c = db.Column(db.String(100))
    _6c = db.Column(db.String(100))
    _7c = db.Column(db.String(100))
    _8c = db.Column(db.String(100))
    _9c = db.Column(db.String(100))
    _10c = db.Column(db.String(100))
    ### 10 stsaji


class Driver(db.Model):
    __tablename__ = "driver"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy

    driver_id = db.Column(db.String(100))
    number = db.Column(db.String(100))
    code = db.Column(db.String(100), unique=True)


class Constructor(db.Model):
    __tablename__ = "constructor"

    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy

    constructorId = db.Column(db.String(100))
    name = db.Column(db.String(100))
    code = db.Column(db.String(100), unique=True)


class BonusGuess(db.Model):
    __tablename__ = "bonusguess"
    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy

    text = db.Column(db.String(500))
    type = db.Column(db.String(100))
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))

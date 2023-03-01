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


from app import db
from datetime import datetime


class Race(db.Model):
    __tablename__ = "race"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    round = db.Column(db.Integer, unique=True)
    country = db.Column(db.String(50))
    circuit_name = db.Column(db.String(50))
    external_circuit_id = db.Column(db.String(50))

    sprint_date = db.Column(db.TIMESTAMP(timezone=True))
    qualification_date = db.Column(db.TIMESTAMP(timezone=True))
    race_date = db.Column(db.TIMESTAMP(timezone=True))
    #type = db.Column(db.String(100))

    @classmethod
    def race_from_data(cls, data):
        if isinstance(data, dict) and "MRData" in data:
            return cls.race_from_data(data["MRData"]["RaceTable"]["Races"])

        if isinstance(data, list):
            return [cls.race_from_data(elem) for elem in data]

        kwargs = {
            # basic data
            "name": data["raceName"],
            "round": int(data["round"]),
            "country": data["Circuit"]["Location"]["country"],
            "circuit_name":  data["Circuit"]["circuitName"],
            "external_circuit_id": data["Circuit"]["circuitId"], 
            
            # dates
            "sprint_date": cls.format_date(data.get("Sprint") or None),
            "qualification_date": cls.format_date(data.get("Qualifying") or None),
            "race_date": cls.format_date(data)         
        }

        return cls(
            **kwargs
        )

    @staticmethod
    def format_date(data):
        if data:
            return datetime.fromisoformat(data["date"] + "T" + data["time"][:-1]) # should be UTC!
        else:
            return None


class RaceResult(db.Model):
    __tablename__ = "raceresult"

    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"), unique=True)

    quali = db.Column(db.String(100))
    sprint = db.Column(db.String(100))

    first = db.Column(db.String(100))
    second = db.Column(db.String(100))
    third = db.Column(db.String(100))

    fastest_lap = db.Column(db.String(100))
    safety_car = db.Column(db.String(100))
    bonus = db.Column(db.String(100))


class Bet(db.Model):
    __tablename__ = "bet"

    id = db.Column(db.Integer, primary_key=True)
    # driver/team/custom/value/number
    value = db.Column(db.String(50))
    # maybe enum type? - 
    # - 1st, 2nd, 3rd, fastest_lap, bonus_question, pole position, sprint winner
    type = db.Column(db.String(50))
    is_ok = db.Column(db.Boolean)
    is_evaluated = db.Column(db.Boolean)
    # FKs  user_id, race_id
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))


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



class BonusQuestion(db.Model):
    __tablename__ = "bonus_question"

    id = db.Column(db.Integer, primary_key=True)
    # driver/team/custom/value/number
    value = db.Column(db.String(50))
    # quali/race/sprint
    type = db.Column(db.String(50))

    # FKs race_id
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))

class Standings(db.Model):
    __tablename__ = "standings"
    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy

    position = db.Column(db.String(20))
    type = db.Column(db.String(100))
    name = db.Column(db.String(20), unique=True)
    points = db.Column(db.String(20))

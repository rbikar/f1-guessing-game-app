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


class Driver(db.Model):
    __tablename__ = "driver"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50),  unique=True)
    external_driver_id = db.Column(db.String(50),  unique=True)
    code = db.Column(db.String(10),  unique=True)
    is_active_for_race = db.Column(db.Boolean)
    is_active_for_season = db.Column(db.Boolean)


class Team(db.Model):
    __tablename__ = "team"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50),  unique=True)
    external_team_id = db.Column(db.String(50),  unique=True)
    code = db.Column(db.String(10),  unique=True)
from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    role: Mapped[Optional[str]]
    email: Mapped[Optional[str]]

    bets: Mapped[list["Bet"]] = relationship(back_populates="user")


FIX_COUNTRY_MAP = {
    "UAE": "AE",
    "UK": "GB",
}


class Race(db.Model):
    __tablename__ = "race"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    round: Mapped[int] = mapped_column(unique=True)
    country: Mapped[str]
    circuit_name: Mapped[str]
    ext_id: Mapped[str]

    sprint_date: Mapped[Optional[datetime]]
    quali_date: Mapped[datetime]
    race_date: Mapped[datetime]
    type: Mapped[str]  # NORMAL | SPRINT

    bonus_bet: Mapped[Optional[str]]
    bonus_bet_type: Mapped[Optional[str]]  # YES, free=form? uvidime, mozna v sezone

    # raceresult_id: Mapped[int] = mapped_column(ForeignKey('raceresult.id'))
    race_results: Mapped[list["RaceResult"]] = relationship()
    bets: Mapped[list["Bet"]] = relationship()

    @classmethod
    def race_from_data(cls, data):
        if isinstance(data, dict) and "MRData" in data:
            return cls.race_from_data(data["MRData"]["RaceTable"]["Races"])

        if isinstance(data, list):
            return [cls.race_from_data(elem) for elem in data]

        kwargs = {  ### tytto kwatgs pripravit jinde a poslat rovnout spravny dict jako kwagrtsf pro Race(**kw)
            # basic data
            "name": data["raceName"],
            "round": int(data["round"]),
            "country": cls.fix_country(data["Circuit"]["Location"]["country"]),
            "circuit_name": data["Circuit"]["circuitName"],
            "ext_id": data["Circuit"]["circuitId"],
            # dates
            "sprint_date": cls.format_date(data.get("Sprint") or None),
            "quali_date": cls.format_date(data.get("Qualifying") or None),
            "race_date": cls.format_date(data),
            "type": "SPRINT" if data.get("Sprint") else "NORMAL",
        }

        return cls(**kwargs)

    @staticmethod
    def format_date(data):
        if data:
            time = data.get("time", [])[:-1] or "00:00:00"
            return datetime.fromisoformat(data["date"] + "T" + time)  # should be UTC!
        else:
            return None

    @staticmethod
    def fix_country(country):
        return FIX_COUNTRY_MAP.get(country, country)


class RaceResult(db.Model):
    __tablename__ = "raceresult"

    id: Mapped[int] = mapped_column(primary_key=True)

    type: Mapped[str]  # RACE, QUALI , SPRINT, FASTEST_LAP, SC, BONUS. DRIVER_OF_THE_DAY
    rank: Mapped[Optional[int]]  # 1..N or null
    competitor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("competitor.id"))
    value: Mapped[Optional[str]]  # for bonus
    race_id: Mapped[int] = mapped_column(ForeignKey("race.id"))

    @classmethod
    def from_data(cls, data):
        if isinstance(data, list):
            return [cls.from_data(elem) for elem in data]

        kwargs = {
            "type": data["type"].upper(),
            "rank": data["rank"],
            "competitor_id": data.get("competitor_id"),
            "value": data.get("value"),
            "race_id": data["race_id"],
        }

        return cls(**kwargs)


class Bet(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)

    type: Mapped[str]  # QUALIE |SPRINT|RACE, FL, SC, BONUS, DOD, SEASON!!!
    rank: Mapped[Optional[int]]
    value: Mapped[Optional[str]]  ### competitor or free for or number
    result: Mapped[int] = mapped_column(default=0)
    extra: Mapped[Optional[str]]  # JOKER

    race_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("race.id")
    )  ## NULLABLE NA SEASON TIP!!!!!!
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="bets")

    @classmethod
    def from_data(cls, data):
        # if isinstance(data, dict):
        #    return cls.from_data(data)

        if isinstance(data, list):
            return [cls.from_data(elem) for elem in data]

        kwargs = {
            "type": data["type"].upper(),
            "rank": data["rank"],
            "value": data["value"],
            "extra": data["extra"],
            "race_id": data["race_id"],
            "user_id": data["user_id"],
        }

        return cls(**kwargs)

    def __repr__(self):
        return f"RACE: {self.race_id}, USER:{self.user.username}, TYPE: {self.type}"


class Competitor(db.Model):
    __tablename__ = "competitor"

    id: Mapped[int] = mapped_column(primary_key=True)
    ext_id: Mapped[str]
    name: Mapped[str]
    code: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
    type: Mapped[str]  # DRIVER|TEAM
    points: Mapped[int] = mapped_column(default=0)
    position: Mapped[int] = mapped_column(default=0)
    # def serialize?
    race_results: Mapped[list["RaceResult"]] = relationship()

    ### tyto dve metody zkusit deduplikovat
    @classmethod
    def drivers_from_data(cls, data):
        if isinstance(data, dict) and "MRData" in data:
            return cls.drivers_from_data(data["MRData"]["DriverTable"]["Drivers"])

        if isinstance(data, list):
            return [cls.drivers_from_data(elem) for elem in data]

        kwargs = {  ### tytto kwatgs pripravit jinde a poslat rovnout spravny dict jako kwagrtsf pro Race(**kw)
            # basic data
            "name": f"{data['givenName']} {data['familyName']}",
            "ext_id": data["driverId"],
            "code": data["code"],
            "type": "DRIVER",
            "active": True,
        }

        return cls(**kwargs)

    @classmethod
    def teams_from_data(cls, data):
        if isinstance(data, dict) and "MRData" in data:
            return cls.teams_from_data(
                data["MRData"]["ConstructorTable"]["Constructors"]
            )

        if isinstance(data, list):
            return [cls.teams_from_data(elem) for elem in data]

        kwargs = {  ### tytto kwatgs pripravit jinde a poslat rovnout spravny dict jako kwagrtsf pro Race(**kw)
            # basic data
            "name": data["name"],
            "ext_id": data["constructorId"],
            "code": "TO_UPDATE",
            "type": "TEAM",
            "active": True,
        }

        return cls(**kwargs)

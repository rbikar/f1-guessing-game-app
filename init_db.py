import sys
import os

from app import db
from app.factory import (
    create_app,
)
from app.ergast_client.client import Client
from app.models import Race, Competitor, RaceResult, User
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select
from app.main import KEY_TYPE_RANK_MAP

dummy_race_results = [
    {
        "type": "RACE",
        "rank": "1",
        "competitor_id": 1,
        "race_id": 1,
    },
    {
        "type": "RACE",
        "rank": "2",
        "competitor_id": 2,
        "race_id": 1,
    },
    {
        "type": "RACE",
        "rank": "3",
        "competitor_id": 3,
        "race_id": 1,
    },
    {
        "type": "QUALI",
        "rank": None,
        "competitor_id": 1,
        "race_id": 1,
    },
    {
        "type": "SC",
        "rank": None,
        "competitor_id": 1,
        "race_id": 1,
    },
    {
        "type": "FASTEST",
        "rank": None,
        "competitor_id": 1,
        "race_id": 1,
    },
    {
        "type": "BONUS",
        "rank": None,
        "value": "vysledek bonusu",
        "race_id": 1,
    },
    {
        "type": "DRIVERDAY",
        "rank": None,
        "competitor_id": 2,
        "race_id": 1,
    },  ###bez sprintu
    {
        "type": "RACE",
        "rank": "1",
        "competitor_id": 1,
        "race_id": 6,
    },
    {
        "type": "RACE",
        "rank": "2",
        "competitor_id": 2,
        "race_id": 6,
    },
    {
        "type": "RACE",
        "rank": "3",
        "competitor_id": 3,
        "race_id": 6,
    },
    {
        "type": "QUALI",
        "rank": None,
        "competitor_id": 1,
        "race_id": 6,
    },
    {
        "type": "SC",
        "rank": None,
        "competitor_id": 1,
        "race_id": 6,
    },
    {
        "type": "FASTEST",
        "rank": None,
        "competitor_id": 1,
        "race_id": 6,
    },
    {
        "type": "BONUS",
        "rank": None,
        "value": "vysledek bonusu",
        "race_id": 6,
    },
    {
        "type": "DRIVERDAY",
        "rank": None,
        "competitor_id": 2,
        "race_id": 6,
    },
    {
        "type": "SPRINT",
        "rank": None,
        "competitor_id": 2,
        "race_id": 6,
    },
]

db_uri = None
if len(sys.argv) == 2:
    db_uri = sys.argv[1]
app = create_app(db_uri)


def empty_result(bet_type, rank, race_id):
    data = {
        "type": bet_type,
        "rank": rank if rank else None,
        "race_id": race_id,
    }

    return RaceResult.from_data(data)


with app.app_context():
    db.create_all()
    with Client("https://api.jolpi.ca/") as client:
        races = Race.race_from_data(client.get_current_schedule().result())
        drivers = Competitor.drivers_from_data(client.get_drivers().result())
        teams = Competitor.teams_from_data(client.get_constructors().result())

        db.session.add_all(races + drivers + teams)

        races = db.session.execute(select(Race)).scalars().all()
        for r in races:
            for val in KEY_TYPE_RANK_MAP.values():
                if r.type == "NORMAL" and val[0] == "SPRINT":
                    continue
                new_item = empty_result(val[0], val[1], r.id)
                db.session.add(new_item)

        if os.getenv("F1TEST"):
            new_user = User(
                username="test",
                password=generate_password_hash("test", method="pbkdf2:sha256"),
            )

            db.session.add(new_user)
            race_results = RaceResult.from_data(dummy_race_results)
            db.session.add_all(race_results)

        db.session.commit()

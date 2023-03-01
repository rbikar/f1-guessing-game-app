import sys

from app import db
from app.factory import (
    create_app,
    load_constructors_to_db,
    load_drivers_to_db,
    load_empty_bonus_guesses_to_db,
)
from app.ergast_client.client import Client
from app.models import Race

db_uri = None
if len(sys.argv) == 2:
    db_uri = sys.argv[1]
app = create_app(db_uri)

with app.app_context():
    db.create_all()
    load_constructors_to_db()
    load_drivers_to_db()

    
    with Client("https://ergast.com") as client:
        schedule = client.get_current_schedule().result()
        races = Race.race_from_data(schedule)
        db.session.add_all(races)
        db.session.commit()

    load_empty_bonus_guesses_to_db()

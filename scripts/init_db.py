import sys
import logging

logging.basicConfig()
from app import db
from app.factory import (
    create_app,
)
from app.models.races import Race
db_uri = None
if len(sys.argv) == 2:
    db_uri = sys.argv[1]
app = create_app(db_uri)

with app.app_context():
    db.create_all()
    from app.ergast_client.client import Client
    
    with Client("https://ergast.com") as client:
        schedule = client.get_current_schedule().result()
        races = Race.race_from_data(schedule)
        db.session.add_all(races)
        db.session.commit()


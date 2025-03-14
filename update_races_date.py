import sys

from app import db
from app.factory import (
    create_app,
)
from app.ergast_client.client import Client
from app.models import Race

db_uri = None
if len(sys.argv) == 2:
    db_uri = sys.argv[1]
app = create_app(db_uri)

with app.app_context():
    
    with Client("https://api.jolpi.ca/") as client:
        schedule = client.get_current_schedule().result()
        new_race_data = Race.race_from_data(schedule)
        
        existing_races_map = {race.ext_id:race for race in db.session.query(Race).all()}

        for new_race in new_race_data:
            race_in_db = existing_races_map[new_race.ext_id]
            print(f"{race_in_db.ext_id}+{race_in_db.race_date}")
            race_in_db.sprint_date = new_race.sprint_date
            race_in_db.quali_date = new_race.quali_date
            race_in_db.race_date = new_race.race_date
        db.session.commit()

import sys

from app import db
from app.factory import (
    create_app,
    load_constructors_to_db,
    load_drivers_to_db,
    load_races,
)

db_uri = None
if len(sys.argv) == 2:
    db_uri = sys.argv[1]
app = create_app(db_uri)

with app.app_context():
    db.create_all()
    load_constructors_to_db()
    load_drivers_to_db()
    load_races()

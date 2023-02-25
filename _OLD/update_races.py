import sys

from app import db
from app.factory import create_app, load_races_to_db

db_uri = None
if len(sys.argv) == 2:
    db_uri = sys.argv[1]
app = create_app(db_uri)

with app.app_context():
    load_races_to_db()

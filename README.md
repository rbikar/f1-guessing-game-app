# f1-guessing-game-app



# dev-env
since flask2.3 use FLASK_DEBUG instead FLASK_ENV

`export F1TEST=1`
`export FLASK_DEBUG=1`
`export FLASK_APP=app/factory.py`

For DB init:

`python init_db.py`

Run dev. server

`flask run`





# flask-migrate

1st migration

`flask db init`

initial migration

`flask db migrate -m "Initial migration."`

upgrade db (connection details has to bet via env vars for non-dev DB)

`flask db upgrade`

everytime use

`flask db migrage -m "some message"`
`flask db upgrade`

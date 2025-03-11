from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy(model_class=Base)

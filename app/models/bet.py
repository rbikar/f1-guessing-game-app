from app import db


class Bet(db.Model):
    __tablename__ = "bet"

    id = db.Column(db.Integer, primary_key=True)
    # driver/team/custom/value/number
    value = db.Column(db.String(50))
    # maybe enum type? - 
    # - 1st, 2nd, 3rd, fastest_lap, bonus_question, pole position, sprint winner
    type = db.Column(db.String(50))
    is_ok = db.Column(db.Boolean)
    is_evaluated = db.Column(db.Boolean)
    # FKs  user_id, race_id
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))


class BonusQuestion(db.Model):
    __tablename__ = "bonus_question"

    id = db.Column(db.Integer, primary_key=True)
    # driver/team/custom/value/number
    value = db.Column(db.String(50))
    # quali/race/sprint
    type = db.Column(db.String(50))

    # FKs race_id
    race_id = db.Column(db.Integer, db.ForeignKey("race.id"))

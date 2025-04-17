from app.results import eval_bet
from app.models import RaceResult, Bet


def test_eval_bet_race():
    data = {"type": "RACE", "rank": 1, "value": "ABC", "user_id": 0}
    bet = Bet.from_data(data)
    data = {"type": "RACE", "rank": 1, "value": "ABC", "race_id": 0}
    result_map = {"RACE_1": RaceResult.from_data(data)}
    bet_result = eval_bet(bet, result_map)
    assert bet_result == 2


def test_eval_bet_race_joker():
    data = {"type": "RACE", "rank": 1, "value": "ABC", "user_id": 0, "extra": "JOKER"}
    bet = Bet.from_data(data)
    data = {"type": "RACE", "rank": 1, "value": "ABC", "race_id": 0}
    result_map = {"RACE_1": RaceResult.from_data(data)}
    bet_result = eval_bet(bet, result_map)
    assert bet_result == 4


def test_eval_bet_podium():
    data = {
        "type": "RACE",
        "rank": 1,
        "value": "ABC",
        "user_id": 0,
    }
    bet = Bet.from_data(data)
    data_1 = {"type": "RACE", "rank": 1, "value": "XXX", "race_id": 0}
    data_2 = {"type": "RACE", "rank": 2, "value": "ABC", "race_id": 0}
    result_map = {
        "RACE_1": RaceResult.from_data(data_1),
        "RACE_2": RaceResult.from_data(data_2),
    }
    bet_result = eval_bet(bet, result_map)
    assert bet_result == 0.5


def test_eval_bet_podium_joker():
    data = {"type": "RACE", "rank": 1, "value": "ABC", "user_id": 0, "extra": "JOKER"}
    bet = Bet.from_data(data)
    data_1 = {"type": "RACE", "rank": 1, "value": "XXX", "race_id": 0}
    data_2 = {"type": "RACE", "rank": 2, "value": "ABC", "race_id": 0}
    result_map = {
        "RACE_1": RaceResult.from_data(data_1),
        "RACE_2": RaceResult.from_data(data_2),
    }
    bet_result = eval_bet(bet, result_map)
    assert bet_result == 1


def test_eval_bet_podium():
    data = {
        "type": "QUALI",
        "rank": 1,
        "value": "ABC",
        "user_id": 0,
    }
    bet = Bet.from_data(data)
    data = {"type": "QUALI", "value": "ABC", "rank": 1, "race_id": 0}
    result_map = {"QUALI": RaceResult.from_data(data)}
    bet_result = eval_bet(bet, result_map)
    assert bet_result == 1


def test_eval_bet_podium_joker():
    # joker not applied to non-Sunday bets
    data = {"type": "QUALI", "rank": 1, "value": "ABC", "user_id": 0, "extra": "JOKER"}
    bet = Bet.from_data(data)
    data = {"type": "QUALI", "value": "ABC", "rank": 1, "race_id": 0}
    result_map = {"QUALI": RaceResult.from_data(data)}
    bet_result = eval_bet(bet, result_map)
    assert bet_result == 1

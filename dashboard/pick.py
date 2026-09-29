import random


def random_squad(players: list[dict]) -> list[dict]:
    squad = []
    budget = 100.0
    for p in random.sample(players, len(players)):
        if p["price"] <= budget and len(squad) < 15:
            squad.append(p)
            budget -= p["price"]
    return squad

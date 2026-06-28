import random
from itertools import product
from functools import lru_cache



def _precompute_round_probs() -> dict[tuple[int, int], dict[tuple[int, int], float]]:
    """Returns {(n_att, n_def): {(att_loss, def_loss): probability}}"""
    table = {}
    for n_att in (1, 2 , 3):
        for n_def in (1, 2):
            outcomes : dict[tuple[int, int], int] = {}
            total = 0
            for att_dice in product(range(1, 7), repeat=n_att):
                for def_dice in product(range(1, 7), repeat=n_def):
                    a_sorted = tuple(sorted(att_dice, reverse=True))
                    d_sorted = tuple(sorted(def_dice, reverse=True))
                    att_loss, def_loss = 0, 0
                    if a_sorted[0] > d_sorted[0]:
                        def_loss += 1
                    else:
                        att_loss += 1
                    if n_att > 1 and n_def > 1:
                        if a_sorted[1] > d_sorted[1]:
                            def_loss += 1
                        else:
                            att_loss += 1
                    outcomes[(att_loss, def_loss)] = outcomes.get((att_loss, def_loss), 0) + 1
                    total += 1
            table[(n_att, n_def)] = {k: v / total for k, v in outcomes.items()}
    return table


def roll_dice(n: int, rng: random.Random) -> list[int]:
    if n < 1 or n > 3:
        raise ValueError
    return sorted([rng.randint(1, 6) for _ in range(n)], reverse=True)

def resolve_round(att_dice: list[int], def_dice: list[int]) -> tuple[int, int]:
    if len(att_dice) > 3 or len(att_dice) < 1:
        raise ValueError
    if len(def_dice) > 2 or len(def_dice) < 1:
        raise ValueError
    att_loss, def_loss = 0, 0
    if att_dice[0] > def_dice[0]:
        def_loss += 1
    else:
        att_loss += 1
    if len(att_dice) > 1 and len(def_dice) > 1:
        if att_dice[1] > def_dice[1]:
            def_loss += 1
        else:
            att_loss += 1
    return (att_loss, def_loss)

def simulate_battle(att_armies: int, def_armies: int, rng: random.Random) -> tuple[int, int, bool]:
    if att_armies < 2 or def_armies < 1:
        raise ValueError
    attacker_won = False
    while att_armies > 1 and def_armies > 0:
        att_dice, def_dice = roll_dice(min(3, att_armies - 1), rng=rng), roll_dice(min(2, def_armies), rng=rng)
        att_loss, def_loss = resolve_round(att_dice=att_dice, def_dice=def_dice)
        att_armies -= att_loss
        def_armies -= def_loss
        if def_armies <= 0:
            attacker_won = True
    return (att_armies, def_armies, attacker_won)

_round_probs = _precompute_round_probs()

@lru_cache(maxsize=None)
def battle_outcome_probs(att_armies: int, def_armies: int) -> dict[str, float]:
    if att_armies < 2:
        raise ValueError
    if def_armies < 1:
        raise ValueError
    max_a, max_d = att_armies, def_armies
    P = [[0.0] * (max_d + 1) for _ in range(max_a + 1)]

    for a in range(max_a + 1):
        P[a][0] = 1.0
    
    for total in range(2, max_a + max_d + 1):
        for a in range(2, max_a + 1):
            d = total - a
            if d < 1 or d > max_d:
                continue
            n_att = min(3, a - 1)
            n_def = min(2, d)
            prob = 0.0
            for (la, ld), p_round in _round_probs[(n_att, n_def)].items():
                prob += p_round * P[a - la][d - ld]
            P[a][d] = prob
    att_win = P[att_armies][def_armies]
    return {"att_win": att_win, "def_win": 1 - att_win}
            
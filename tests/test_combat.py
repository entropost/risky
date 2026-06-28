import random
import pytest
from risky.engine.combat import roll_dice, resolve_round, simulate_battle, battle_outcome_probs

@pytest.fixture
def rng():
    return random.Random(42)

def test_roll_dice_count(rng):
    assert(len(roll_dice(1, rng))) == 1
    assert(len(roll_dice(2, rng))) == 2
    assert(len(roll_dice(3, rng))) == 3

def test_roll_dice_sorted_desc(rng):
    for _ in range(100):
        result = roll_dice(3, rng)
        assert(result == sorted(result, reverse=True))

def test_roll_dice_values_in_range(rng):
    for _ in range(100):
        result = roll_dice(3, rng)
        for x in result:
            assert(1 <= x <= 6)

def test_roll_dice_deterministic(rng):
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    for _ in range(10):
        assert(roll_dice(3, rng1) == roll_dice(3, rng2))

def test_roll_dice_returns_list(rng):
    assert(isinstance(roll_dice(3, rng), list))

def test_roll_dice_bad_n_zero(rng):
    with pytest.raises(ValueError):
        roll_dice(0, rng)

def test_roll_dice_bad_n_four(rng):
    with pytest.raises(ValueError):
        roll_dice(4, rng)

def test_roll_dice_distribution():
    r = random.Random(42)
    counts = {i: 0 for i in range(1, 7)}
    for _ in range(6000):
        for x in roll_dice(3, r):
            counts[x] += 1
    for face in range(1, 7):
        assert 2700 <= counts[face] <= 3300


def test_resolve_1v1_att_wins():
    assert resolve_round([4], [3]) == (0, 1)

def test_resolve_1v1_def_win_tie():
    assert resolve_round([3], [3]) == (1, 0)

def test_resolve_1v1_def_win_higher():
    assert resolve_round([2], [5]) == (1, 0)

def test_resolve_1v2_one_comparison():
    assert resolve_round([6], [5, 4]) == (0, 1)

def test_resolve_2v1_one_comparison():
    assert resolve_round([5, 2], [4]) == (0, 1)

def test_resolve_2v2_split():
    assert resolve_round([4, 2], [3, 3]) == (1, 1)

def test_resolve_2v2_att_loses_both():
    assert resolve_round([3, 1], [4, 1]) == (2, 0)

def test_resolve_3v2_def_loses_both():
    assert resolve_round([6, 5, 1], [4, 2]) == (0, 2)

def test_resolve_3v2_split():
    assert resolve_round([6, 5, 1], [6, 2]) == (1, 1)

def test_resolve_3v1_one_comparison():
    assert resolve_round([4, 2, 1], [5]) == (1, 0)

def test_resolve_bad_att_empty(rng):
    with pytest.raises(ValueError):
        resolve_round([], [4])

def test_resolve_bad_att_four(rng):
    with pytest.raises(ValueError):
        resolve_round([6, 4, 3, 2], [4])

def test_resolve_bad_def_three(rng):
    with pytest.raises(ValueError):
        resolve_round([5], [6, 3, 1])


def test_simulate_deterministic():
    r1 = random.Random(42)
    r2 = random.Random(42)
    assert simulate_battle(5, 3, r1) == simulate_battle(5, 3, r2)

def test_simulate_att_always_at_least_one(rng):
    for a, d in [(2, 1), (3, 2), (5, 5), (10, 10), (50, 50)]:
        att_rem, _, _ = simulate_battle(a, d, rng)
        assert att_rem >= 1

def test_simulate_def_zero_iff_won(rng):
    for a, d in [(2, 1), (3, 2), (5, 5), (10, 10), (50, 50)]:
        _, def_rem, won = simulate_battle(a, d, rng)
        assert (def_rem == 0) == won

def test_simulate_att_not_enough(rng):
    with pytest.raises(ValueError):
        simulate_battle(1, 5, rng)

def test_simulate_att_not_enough_zero(rng):
    with pytest.raises(ValueError):
        simulate_battle(0, 1, rng)

def test_simulate_def_zero_raises(rng):
    with pytest.raises(ValueError):
        simulate_battle(3, 0, rng)

def test_simulate_armies_non_increasing(rng):
    for a, d in [(2, 1), (3, 2), (5, 5), (10, 10), (50, 50), (20, 5)]:
        att_rem, def_rem, _ = simulate_battle(a, d, rng)
        assert att_rem + def_rem <= a + d

def test_simulate_2v1_can_lose():
    for _ in range(200):
        r = random.Random()
        _, _, won = simulate_battle(2, 1, r)
        if not won:
            break
    else:
        pytest.fail("2v1 never lost after 200 attempts.")


def test_probs_2v1():
    p = battle_outcome_probs(2, 1)
    assert p["att_win"] == pytest.approx(5/12, rel=1e-10)

def test_probs_3v1():
    p = battle_outcome_probs(3, 1)
    assert p["att_win"] == pytest.approx(0.7542438272, rel=1e-10)

def test_probs_3v2():
    p = battle_outcome_probs(3, 2)
    assert p["att_win"] == pytest.approx(0.3626543210, rel=1e-10)

def test_probs_4v2():
    p = battle_outcome_probs(4, 2)
    assert p["att_win"] == pytest.approx(0.6559539998, rel=1e-10)

def test_probs_5v5():
    p = battle_outcome_probs(5, 5)
    assert p["att_win"] == pytest.approx(0.3586062332, rel=1e-10)

def test_probs_10v5():
    p = battle_outcome_probs(10, 5)
    assert p["att_win"] == pytest.approx(0.8729364727, rel=1e-10)

def test_probs_10v10():
    p = battle_outcome_probs(10, 10)
    assert p["att_win"] == pytest.approx(0.4799352565, rel=1e-10)

def test_probs_15v10():
    p = battle_outcome_probs(15, 10)
    assert p["att_win"] == pytest.approx(0.8345705609, rel=1e-10)

def test_probs_20v20():
    p = battle_outcome_probs(20, 20)
    assert p["att_win"] == pytest.approx(0.5774574026, rel=1e-10)

def test_probs_100v100():
    p = battle_outcome_probs(100, 100)
    assert p["att_win"] == pytest.approx(0.8079031789, rel=1e-10)

def test_probs_200v100():
    p = battle_outcome_probs(200, 100)
    assert p["att_win"] == pytest.approx(0.9999999997, rel=1e-10)

def test_probs_200v200():
    p = battle_outcome_probs(200, 200)
    assert p["att_win"] == pytest.approx(0.9038658101, rel=1e-10)

def test_probs_sums_to_one_large():
    p = battle_outcome_probs(50, 30)
    assert p["att_win"] + p["def_win"] == pytest.approx(1.0)

def test_probs_sums_to_one_small():
    p = battle_outcome_probs(3, 2)
    assert p["att_win"] + p["def_win"] == pytest.approx(1.0)

def test_probs_monotonic_in_att():
    assert battle_outcome_probs(6, 5)["att_win"] > battle_outcome_probs(5, 5)["att_win"]

def test_probs_monotonic_in_def():
    assert battle_outcome_probs(5, 6)["att_win"] < battle_outcome_probs(5, 5)["att_win"]

def test_probs_between_zero_and_one():
    for a in range(2, 21):
        for d in range(1, 21):
            p = battle_outcome_probs(a, d)
            assert 0.0 <= p["att_win"] <= 1.0
            assert 0.0 <= p["def_win"] <= 1.0

def test_probs_bad_input_att():
    with pytest.raises(ValueError):
        battle_outcome_probs(1, 5)

def test_probs_bad_input_def():
    with pytest.raises(ValueError):
        battle_outcome_probs(3, 0)

def test_probs_cache_works():
    battle_outcome_probs(200, 200)
    p = battle_outcome_probs(200, 200)
    assert p["att_win"] == pytest.approx(0.9038658101, rel=1e-10)
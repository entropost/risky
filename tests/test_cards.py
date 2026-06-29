import random
from collections import Counter

import pytest

from risky.engine.map import GameMap
from risky.engine.state import Card, Symbol, GameState, Phase
from risky.engine.cards import (
    SetKind, TradeSet, DEFAULT_FIXED_VALUES,
    create_deck, shuffle, draw, discard_to_pile,
    find_valid_sets, has_valid_set, must_trade,
    fixed_trade_value, territory_bonus,
)


def _tiny_map(territory_names: list[str]) -> GameMap:
    n = len(territory_names)
    territories = {}
    for i, name in enumerate(territory_names):
        prev_name = territory_names[(i - 1) % n]
        next_name = territory_names[(i + 1) % n]
        adj = [prev_name, next_name] if n > 1 else [prev_name]
        if n == 2 and prev_name == next_name:
            adj = [next_name]
        territories[name] = {"continent": "C", "adjacent": adj}
    return GameMap.from_dict({
        "continents": {"C": {"bonus": 1, "territories": territory_names}},
        "territories": territories,
    })


def _make_state(
    owners: dict[str, str] | None = None,
    player: str = "P1",
    current_phase: Phase = Phase.DEPLOY,
) -> GameState:
    tiny = _tiny_map(["A", "B", "C", "D", "E", "F", "G", "H", "I"])
    all_owners = {t: "P1" for t in tiny.territories}
    if owners is not None:
        all_owners.update(owners)
    return GameState(
        map=tiny,
        owners=all_owners,
        armies={t: 1 for t in tiny.territories},
        player_hands={},
        deck=(),
        discards=(),
        trade_in_counts= {o: 0 for o in owners.values()},
        current_player=player,
        current_phase=current_phase,
    )


I_A = Card(territory="A", symbol=Symbol.INFANTRY)
I_B = Card(territory="B", symbol=Symbol.INFANTRY)
I_C = Card(territory="C", symbol=Symbol.INFANTRY)
C_A = Card(territory="D", symbol=Symbol.CAVALRY)
C_B = Card(territory="E", symbol=Symbol.CAVALRY)
C_C = Card(territory="F", symbol=Symbol.CAVALRY)
A_A = Card(territory="G", symbol=Symbol.ARTILLERY)
A_B = Card(territory="H", symbol=Symbol.ARTILLERY)
A_C = Card(territory="I", symbol=Symbol.ARTILLERY)
W_1 = Card(territory=None, symbol=Symbol.WILD)
W_2 = Card(territory=None, symbol=Symbol.WILD)
W_3 = Card(territory=None, symbol=Symbol.WILD)


def test_create_deck_length_classic():
    deck = create_deck(GameMap.classic())
    assert len(deck) == 44

def test_create_deck_length_tiny_2():
    m = _tiny_map(["A", "B"])
    deck = create_deck(m, wild_count=0)
    assert len(deck) == 2

def test_create_deck_length_tiny_5():
    m = _tiny_map(["A", "B", "C", "D", "E"])
    deck = create_deck(m, wild_count=0)
    assert len(deck) == 5

def test_create_deck_length_tiny_10():
    m = _tiny_map([str(i) for i in range(10)])
    deck = create_deck(m, wild_count=0)
    assert len(deck) == 10

def test_create_deck_with_custom_wild_count():
    m = _tiny_map(["A", "B", "C", "D", "E"])
    deck = create_deck(m, wild_count=5)
    assert len(deck) == 10

def test_create_deck_zero_wilds():
    deck = create_deck(GameMap.classic(), wild_count=0)
    assert all((c.symbol != Symbol.WILD) and (c.territory is not None) for c in deck)

def test_create_deck_every_territory_once():
    m = GameMap.classic()
    deck = create_deck(m)
    territory_names = [c.territory for c in deck if c.territory is not None]
    counts = Counter(territory_names)
    assert len(territory_names) == len(m.territories)
    for name in m.territories:
        assert counts[name] == 1, f"{name!r} appears {counts[name]} times"

def test_create_deck_symbol_distribution_42():
    m = GameMap.classic()
    deck = create_deck(m)
    symbols = Counter(c.symbol for c in deck)
    assert symbols[Symbol.INFANTRY] == 14
    assert symbols[Symbol.CAVALRY] == 14
    assert symbols[Symbol.ARTILLERY] == 14

def test_create_deck_symbol_distribution_10():
    m = _tiny_map([str(i) for i in range(10)])
    deck = create_deck(m, wild_count=0)
    symbols = Counter(c.symbol for c in deck)
    assert symbols[Symbol.INFANTRY] == 4
    assert symbols[Symbol.CAVALRY] == 3
    assert symbols[Symbol.ARTILLERY] == 3

def test_create_deck_symbol_distribution_5():
    m = _tiny_map(["A", "B", "C", "D", "E"])
    deck = create_deck(m, wild_count=0)
    symbols = Counter(c.symbol for c in deck)
    assert symbols[Symbol.INFANTRY] == 2
    assert symbols[Symbol.CAVALRY] == 2
    assert symbols[Symbol.ARTILLERY] == 1

def test_create_deck_wild_territory_is_none():
    m = GameMap.classic()
    deck = create_deck(m, wild_count=2)
    wilds = [c for c in deck if c.symbol == Symbol.WILD]
    assert len(wilds) == 2
    assert all(c.territory is None for c in wilds)

def test_create_deck_deterministic():
    m = GameMap.classic()
    deck1 = create_deck(m)
    deck2 = create_deck(m)
    assert deck1 == deck2


def test_shuffle_preserves_length():
    deck = create_deck(GameMap.classic())
    rng = random.Random(42)
    shuf = shuffle(deck, rng)
    assert len(shuf) == len(deck)

def test_shuffle_preserves_multiset():
    deck = create_deck(GameMap.classic())
    rng = random.Random(42)
    shuf = shuffle(deck, rng)
    assert Counter(shuf) == Counter(deck)

def test_shuffle_deterministic_same_seed():
    deck = create_deck(GameMap.classic())
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    assert shuffle(deck, rng1) == shuffle(deck, rng2)

def test_shuffle_different_seed_different_order():
    deck = create_deck(GameMap.classic())
    rng1 = random.Random(42)
    rng2 = random.Random(99)
    assert shuffle(deck, rng1) != shuffle(deck, rng2)

def test_shuffle_leaves_input_unchanged():
    deck = create_deck(GameMap.classic())
    original = tuple(deck)
    shuffle(deck, random.Random(42))
    assert deck == original

def test_shuffle_empty_and_single():
    rng = random.Random(42)
    assert shuffle((), rng) == ()
    card = Card(territory="A", symbol=Symbol.INFANTRY)
    assert shuffle((card,), rng) == (card,)


def test_draw_returns_top_card():
    deck = (I_A, I_B, I_C)
    rng = random.Random(42)
    card, new_deck, _ = draw(deck, (), rng)
    assert card == I_C
    assert new_deck == (I_A, I_B)

def test_draw_reduces_deck_by_one():
    deck = create_deck(GameMap.classic())
    rng = random.Random(42)
    _, new_deck, _ = draw(deck, (), rng)
    assert len(new_deck) == len(deck) - 1

def test_draw_leaves_discards_unchanged():
    deck = (I_A, I_B, I_C)
    discards = (A_A, C_A)
    rng = random.Random(42)
    _, _, new_discards = draw(deck, discards, rng)
    assert new_discards == discards

def test_draw_deterministic():
    deck = (I_A, I_B, I_C)
    discards = (C_A,)
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    assert draw(deck, discards, rng1) == draw(deck, discards, rng2)

def test_draw_reshuffles_when_deck_empty():
    discards = (I_A, I_B, I_C)
    rng = random.Random(42)
    card, new_deck, new_discards = draw((), discards, rng)
    assert card is not None
    assert new_discards == ()
    assert len(new_deck) == len(discards) - 1

def test_draw_reshuffle_uses_rng():
    discards = create_deck(GameMap.classic())
    rng1 = random.Random(42)
    rng2 = random.Random(99)
    _, deck1, _ = draw((), discards, rng1)
    _, deck2, _ = draw((), discards, rng2)
    assert deck1 != deck2

def test_draw_both_empty_returns_none():
    rng = random.Random(42)
    card, new_deck, new_discards = draw((), (), rng)
    assert card is None
    assert new_deck == ()
    assert new_discards == ()

def test_draw_full_cycle_44_cards():
    deck = create_deck(GameMap.classic())
    discards: tuple[Card, ...] = ()
    rng = random.Random(42)

    drawn: list[Card] = []
    for _ in range(44):
        card, deck, discards = draw(deck, discards, rng)
        assert card is not None
        drawn.append(card)

    assert len(deck) == 0

    discards = discard_to_pile(tuple(drawn), discards)
    assert len(discards) == 44

    for _ in range(44):
        card, deck, discards = draw(deck, discards, rng)
        assert card is not None

    assert len(deck) == 0

def test_discard_appends_to_empty():
    result = discard_to_pile((I_A,), ())
    assert result == (I_A,)

def test_discard_appends_to_existing():
    discards = (I_A, I_B)
    result = discard_to_pile((I_C,), discards)
    assert result == (I_A, I_B, I_C)

def test_discard_multiple_cards():
    discards = (I_A,)
    result = discard_to_pile((C_A, A_A), discards)
    assert result == (I_A, C_A, A_A)

def test_discard_leaves_input_unchanged():
    cards = (I_A, C_A)
    discards = (A_A,)
    snapshot_c = tuple(cards)
    snapshot_d = tuple(discards)
    discard_to_pile(cards, discards)
    assert cards == snapshot_c
    assert discards == snapshot_d

def test_find_valid_sets_empty_hand():
    assert find_valid_sets(()) == []

def test_find_valid_sets_too_few_cards():
    assert find_valid_sets((I_A, I_B)) == []

def test_find_valid_sets_three_infantry():
    result = find_valid_sets((I_A, I_B, I_C))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_INFANTRY)

def test_find_valid_sets_three_cavalry():
    result = find_valid_sets((C_A, C_B, C_C))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_CAVALRY)

def test_find_valid_sets_three_artillery():
    result = find_valid_sets((A_A, A_B, A_C))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_ARTILLERY)

def test_find_valid_sets_one_of_each():
    result = find_valid_sets((I_A, C_A, A_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_two_inf_one_cav_no_set():
    assert find_valid_sets((I_A, I_B, C_A)) == []

def test_find_valid_sets_one_wild_two_infantry():
    result = find_valid_sets((W_1, I_A, I_B))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_INFANTRY)

def test_find_valid_sets_one_wild_two_cavalry():
    result = find_valid_sets((W_1, C_A, C_B))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_CAVALRY)

def test_find_valid_sets_one_wild_two_artillery():
    result = find_valid_sets((W_1, A_A, A_B))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_ARTILLERY)

def test_find_valid_sets_one_wild_infantry_cavalry():
    result = find_valid_sets((W_1, I_A, C_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_one_wild_infantry_artillery():
    result = find_valid_sets((W_1, I_A, A_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_one_wild_cavalry_artillery():
    result = find_valid_sets((W_1, C_A, A_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_two_wilds_one_infantry():
    # ONE_OF_EACH (10) > THREE_INFANTRY (4)
    result = find_valid_sets((W_1, W_2, I_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_two_wilds_one_cavalry():
    # ONE_OF_EACH (10) > THREE_CAVALRY (6)
    result = find_valid_sets((W_1, W_2, C_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_two_wilds_one_artillery():
    # ONE_OF_EACH (10) > THREE_ARTILLERY (8)
    result = find_valid_sets((W_1, W_2, A_A))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)

def test_find_valid_sets_three_wilds():
    result = find_valid_sets((W_1, W_2, W_3))
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_WILD)

def test_find_valid_sets_multiple_sets_in_hand():
    hand = (I_A, I_B, I_C, C_A, A_A)
    result = find_valid_sets(hand)
    # Should find at least: (0,1,2) → THREE_INFANTRY and (0,3,4) → ONE_OF_EACH
    assert len(result) >= 2
    kinds = {(ts.indices, ts.kind) for ts in result}
    assert ((0, 1, 2), SetKind.THREE_INFANTRY) in kinds
    assert ((0, 3, 4), SetKind.ONE_OF_EACH) in kinds
    print(result)
    print(kinds)


def test_custom_values_override_ambiguity():
    custom = {**DEFAULT_FIXED_VALUES, SetKind.THREE_CAVALRY: 15}
    result = find_valid_sets((W_1, W_2, C_A), values=custom)
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.THREE_CAVALRY)

def test_custom_values_one_of_each_still_beats():
    custom = {**DEFAULT_FIXED_VALUES, SetKind.ONE_OF_EACH: 12}
    result = find_valid_sets((W_1, W_2, I_A), values=custom)
    assert len(result) == 1
    assert result[0] == TradeSet(indices=(0, 1, 2), kind=SetKind.ONE_OF_EACH)


def test_has_valid_set_true():
    assert has_valid_set((I_A, I_B, I_C)) is True

def test_has_valid_set_false():
    assert has_valid_set((I_A, I_B, C_A)) is False

def test_has_valid_set_empty():
    assert has_valid_set(()) is False


def test_must_trade_5_cards():
    assert must_trade((I_A, I_B, I_C, C_A, A_A)) is True

def test_must_trade_6_cards():
    assert must_trade((I_A, I_B, I_C, C_A, C_B, A_A)) is True

def test_must_trade_4_cards():
    assert must_trade((I_A, I_B, I_C, C_A)) is False

def test_must_trade_empty():
    assert must_trade(()) is False


def test_value_three_infantry():
    assert fixed_trade_value(SetKind.THREE_INFANTRY) == 4

def test_value_three_cavalry():
    assert fixed_trade_value(SetKind.THREE_CAVALRY) == 6

def test_value_three_artillery():
    assert fixed_trade_value(SetKind.THREE_ARTILLERY) == 8

def test_value_one_of_each():
    assert fixed_trade_value(SetKind.ONE_OF_EACH) == 10

def test_value_three_wild():
    assert fixed_trade_value(SetKind.THREE_WILD) == 10

def test_value_custom_dict():
    assert fixed_trade_value(SetKind.THREE_INFANTRY, {SetKind.THREE_INFANTRY: 99}) == 99

def test_value_default_dict_unchanged():
    assert fixed_trade_value(SetKind.THREE_INFANTRY, None) == 4

def test_bonus_owned_territory():
    state = _make_state(owners={"A": "P1", "B": "P1", "C": "P1"})
    hand = (I_A, I_B, A_A)
    bonus, name = territory_bonus((0, 1, 2), hand, state, "P1")
    assert bonus == 2
    assert name == "A"

def test_bonus_no_match():
    state = _make_state(owners={"A": "P2", "B": "P2", "C": "P2"})
    hand = (I_A, I_B, I_C)
    bonus, name = territory_bonus((0, 1, 2), hand, state, "P1")
    assert name is None
    assert bonus == 0

def test_bonus_wild_ignored():
    state = _make_state(owners={"A": "P1", "D": "P2"})
    hand = (W_1, I_A, C_A)
    bonus, name = territory_bonus((0, 1, 2), hand, state, "P1")
    assert bonus == 2
    assert name == "A"

def test_bonus_first_match_wins():
    state = _make_state(owners={"A": "P1", "B": "P1", "G": "P1"})
    hand = (I_A, I_B, A_A)
    bonus, name = territory_bonus((0, 1, 2), hand, state, "P1")
    assert bonus == 2
    assert name == "A"

    hand = (A_A, I_B, I_A)
    bonus, name = territory_bonus((0, 1, 2), hand, state, "P1")
    assert bonus == 2
    assert name == "G"

def test_bonus_wrong_player():
    state = _make_state(owners={"A": "P1"})
    hand = (I_A, I_B, A_A)
    bonus, name = territory_bonus((0, 1, 2), hand, state, "P2")
    assert bonus == 0
    assert name is None


def test_five_card_guarantee():
    """Any 5-card hand drawn from the classic deck must contain a valid set."""
    deck = list(create_deck(GameMap.classic()))
    rng = random.Random(42)
    for _ in range(1000):
        hand = tuple(rng.sample(deck, 5))
        assert has_valid_set(hand), f"No valid set in hand: {hand}"

def test_card_invariant_44():
    m = GameMap.classic()
    deck = create_deck(m)
    discards: tuple[Card, ...] = ()
    p1_hand: tuple[Card, ...] = ()
    p2_hand: tuple[Card, ...] = ()
    rng = random.Random(42)

    def total_cards() -> int:
        return len(deck) + len(discards) + len(p1_hand) + len(p2_hand)

    assert total_cards() == 44

    for _ in range(5):
        card, deck, discards = draw(deck, discards, rng)
        p1_hand = p1_hand + (card,)
    assert total_cards() == 44

    for _ in range(5):
        card, deck, discards = draw(deck, discards, rng)
        p2_hand = p2_hand + (card,)
    assert total_cards() == 44

    # P1 trades a set (discard 3 cards from hand)
    sets = find_valid_sets(p1_hand)
    assert sets, "P1 hand should have a valid set"
    trade_indices = sets[0].indices
    traded = tuple(p1_hand[i] for i in trade_indices)
    discards = discard_to_pile(traded, discards)
    p1_hand = tuple(c for idx, c in enumerate(p1_hand) if idx not in trade_indices)
    assert total_cards() == 44

    for _ in range(100):
        if len(deck) == 0 and len(discards) == 0:
            break
        card, deck, discards = draw(deck, discards, rng)
        p1_hand = p1_hand + (card,)
        assert total_cards() == 44

    assert total_cards() == 44
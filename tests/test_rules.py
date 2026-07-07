from risky.engine import (
    GameMap, GameState, Phase, Symbol, Card,
    DeployAction, AttackAction, FortifyAction, TradeCardsAction, EndPhaseAction,
    validate_deploy, validate_attack, validate_fortify,
    validate_trade, validate_end_phase, has_friendly_path,
)


def _tiny_map() -> GameMap:
    return GameMap.from_dict({
        "continents": {"TinyCont": {"bonus": 1, "territories": ["A", "B", "C"]}},
        "territories": {
            "A": {"continent": "TinyCont", "adjacent": ["B"]},
            "B": {"continent": "TinyCont", "adjacent": ["A", "C"]},
            "C": {"continent": "TinyCont", "adjacent": ["B"]},
        },
    })

def _make_state(
    map: GameMap | None = None,
    owners: dict[str, str] | None = None,
    armies: dict[str, int] | None = None,
    player_hands: dict[str, tuple[Card, ...]] | None = None,
    deck: tuple[Card, ...] | None = None,
    discards: tuple[Card, ...] | None = None,
    trade_in_counts: dict[str, int] | None = None,
    current_player: str = "P1",
    current_phase: Phase = Phase.DEPLOY,
    eliminated: frozenset[str] | None = None,
    turn_number: int = 0,
    conquered_this_turn: bool = False,
) -> GameState:
    gm = map if map is not None else _tiny_map()
    if owners is None:
        owners = {t: "P1" for t in gm.territories}
    if armies is None:
        armies = {t: 1 for t in gm.territories}
    if player_hands is None:
        player_hands = {}
    if deck is None:
        deck = ()
    if discards is None:
        discards = ()
    if trade_in_counts is None:
        trade_in_counts = {"P1": 0}
    if eliminated is None:
        eliminated = frozenset()
    return GameState(
        map=gm, owners=owners, armies=armies,
        player_hands=player_hands, deck=deck, discards=discards,
        trade_in_counts=trade_in_counts,
        current_player=current_player, current_phase=current_phase,
        eliminated=eliminated, turn_number=turn_number,
        conquered_this_turn=conquered_this_turn,
    )

I_A = Card(territory="A", symbol=Symbol.INFANTRY)
I_B = Card(territory="B", symbol=Symbol.INFANTRY)
I_C = Card(territory="C", symbol=Symbol.INFANTRY)
C_D = Card(territory="D", symbol=Symbol.CAVALRY)
A_E = Card(territory="E", symbol=Symbol.ARTILLERY)
W_1 = Card(territory=None, symbol=Symbol.WILD)


class TestValidateDeploy:

    def test_valid_single_placement(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
        )
        action = DeployAction(player="P1", allocations={"A": 3})
        assert validate_deploy(state, action) == []

    def test_valid_batch_placement(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 1, "B": 1, "C": 1},
        )
        action = DeployAction(player="P1", allocations={"A": 4, "B": 2})
        assert validate_deploy(state, action) == []

    def test_wrong_phase(self):
        state = _make_state(current_phase=Phase.ATTACK)
        action = DeployAction(player="P1", allocations={"A": 3})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("DEPLOY" in e for e in errors)
    
    def test_wrong_player(self):
        state = _make_state(current_player="P2")
        action = DeployAction(player="P1", allocations={"A": 3})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("P2" in e or "turn" in e.lower() for e in errors)

    def test_enemy_territory(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 1, "B": 1, "C": 1},
        )
        action = DeployAction(player="P1", allocations={"B": 5})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("B" in e for e in errors)
    
    def test_nonexistent_territory(self):
        state = _make_state()
        action = DeployAction(player="P1", allocations={"X": 3})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("X" in e and "not exist" in e.lower() for e in errors)

    def test_zero_allocation(self):
        state = _make_state()
        action = DeployAction(player="P1", allocations={"A": 0})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("at least 1" in e for e in errors)

    def test_negative_allocation(self):
        state = _make_state()
        action = DeployAction(player="P1", allocations={"A": -1})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("-1" in e for e in errors)

    def test_empty_allocations(self):
        state = _make_state()
        action = DeployAction(player="P1", allocations={})
        errors = validate_deploy(state, action)
        assert len(errors) >= 1
        assert any("at least one" in e.lower() for e in errors)

    def test_multiple_errors_accumulated(self):
        state = _make_state(
            owners={"A": "P2", "B": "P2", "C": "P2"},
            current_phase=Phase.ATTACK,
            current_player="P2",
        )
        action = DeployAction(player="P1", allocations={"X": 0, "A": -1})
        errors = validate_deploy(state, action)
        assert len(errors) >= 5

    def test_territory_not_in_map_but_owned(self):
        state = _make_state(owners={"A": "P1", "Ghost": "P1"})
        action = DeployAction(player="P1", allocations={"Ghost": 3})
        errors = validate_deploy(state, action)
        assert errors == [] # Deploy validator does not check map membership; owners assumed valid


class TestValidateAttack:

    def test_valid_attack_4_armies_3_dice(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=3)
        assert validate_attack(state, action) == []

    def test_valid_attack_2_armies_1_die(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 2, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=1)
        assert validate_attack(state, action) == []

    def test_valid_attack_3_armies_2_dice(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 3, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=2)
        assert validate_attack(state, action) == []

    def test_valid_attack_100_armies_3_dice(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 100, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=3)
        assert validate_attack(state, action) == []

    def test_wrong_phase(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.DEPLOY,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("ATTACK" in e for e in errors)

    def test_wrong_player(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
            current_player="P2",
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("P2" in e or "turn" in e.lower() for e in errors)

    def test_source_not_owned(self):
        state = _make_state(
            owners={"A": "P2", "B": "P1", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="C", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("A" in e and "not owned" in e.lower() for e in errors)

    def test_source_nonexistent(self):
        state = _make_state(
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="X", target="B", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("X" in e and "not exist" in e.lower() for e in errors)

    def test_target_is_own_territory(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("another player" in e.lower() for e in errors)

    def test_target_nonexistent(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="X", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("X" in e and "not exist" in e.lower() for e in errors)

    def test_not_adjacent(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="C", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("not adjacent" in e.lower() for e in errors)

    def test_insufficient_armies_1(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 1, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=1)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("at least 2" in e.lower() for e in errors)

    def test_dice_too_high_3_armies_3_dice(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 3, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=3)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("leave" in e.lower() for e in errors)

    def test_dice_too_high_2_armies_2_dice(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 2, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=2)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("leave" in e.lower() for e in errors)

    def test_dice_count_0(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=0)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("1, 2, or 3" in e or "dice" in e.lower() for e in errors)

    def test_dice_count_4(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=4)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("1, 2, or 3" in e or "dice" in e.lower() for e in errors)

    def test_source_0_armies(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 0, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=1)
        errors = validate_attack(state, action)
        assert len(errors) >= 1
        assert any("at least 2" in e.lower() for e in errors)

    def test_multiple_errors_accumulated(self):
        state = _make_state(
            current_phase=Phase.DEPLOY,
            current_player="P2",
            owners={"A": "P2", "B": "P2", "C": "P2"},
            armies={"A": 1, "B": 1, "C": 1},
        )
        action = AttackAction(player="P1", source="A", target="X", dice_count=4)
        errors = validate_attack(state, action)
        assert len(errors) >= 5

    def test_attack_on_eliminated_player_territory(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P1"},
            armies={"A": 4, "B": 1, "C": 1},
            current_phase=Phase.ATTACK,
            eliminated=frozenset({"P2"}),
        )
        action = AttackAction(player="P1", source="A", target="B", dice_count=3)
        assert validate_attack(state, action) == []


class TestValidateFortify:

    def test_valid_adjacent_fortify(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=2)
        assert validate_fortify(state, action) == []

    def test_valid_multihop_fortify(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            armies={"A": 5, "B": 1, "C": 3},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="C", army_count=2)
        assert validate_fortify(state, action) == []

    def test_valid_entire_stack_minus_one(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=4)
        assert validate_fortify(state, action) == []

    def test_wrong_phase(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.DEPLOY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("FORTIFY" in e for e in errors)

    def test_wrong_player(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
            current_player="P2",
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("P2" in e or "turn" in e.lower() for e in errors)

    def test_source_not_owned(self):
        state = _make_state(
            owners={"A": "P2", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("A" in e and "not owned" in e.lower() for e in errors)

    def test_target_not_owned(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("B" in e and "not owned" in e.lower() for e in errors)

    def test_source_equals_target_no_crash(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="A", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("different" in e.lower() for e in errors)

    def test_zero_transfer(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=0)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("at least 1" in e.lower() for e in errors)

    def test_transfer_leaves_0(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=5)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("leave" in e.lower() for e in errors)

    def test_source_has_1_army_any_transfer_leaves_0(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 1, "B": 5, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=1)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1

    def test_no_friendly_path(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P1"},
            armies={"A": 5, "B": 1, "C": 3},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="C", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("no friendly path" in e.lower() for e in errors)

    def test_source_nonexistent(self):
        state = _make_state(
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="X", target="A", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("X" in e and "not exist" in e.lower() for e in errors)

    def test_target_nonexistent(self):
        state = _make_state(
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="X", army_count=2)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("X" in e and "not exist" in e.lower() for e in errors)

    def test_negative_transfer(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=-1)
        errors = validate_fortify(state, action)
        assert len(errors) >= 1
        assert any("-1" in e for e in errors)

    def test_multiple_errors_accumulated(self):
        state = _make_state(
            current_phase=Phase.DEPLOY,
            current_player="P2",
            owners={"A": "P2", "B": "P2", "C": "P2"},
            armies={"A": 1, "B": 1, "C": 1},
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=0)
        errors = validate_fortify(state, action)
        assert len(errors) >= 5

    def test_friendly_path_not_checked_when_other_errors_exist(self):
        state = _make_state(
            owners={"A": "P1", "B": "P2", "C": "P1"},
            armies={"A": 5, "B": 1, "C": 3},
            current_phase=Phase.FORTIFY,
        )
        action = FortifyAction(player="P1", source="A", target="B", army_count=2)
        errors = validate_fortify(state, action)
        assert any("not owned" in e.lower() for e in errors)
        assert not any("no friendly path" in e.lower() for e in errors)


class TestValidateTrade:

    def test_valid_trade_three_infantry(self):
        state = _make_state(
            owners={"A": "P2", "B": "P2", "C": "P2"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        assert validate_trade(state, action) == []

    def test_valid_trade_with_wild(self):
        state = _make_state(
            owners={"A": "P2", "B": "P2", "C": "P2"},
            player_hands={"P1": (I_A, I_B, W_1)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        assert validate_trade(state, action) == []

    def test_valid_trade_with_bonus(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory="A")
        assert validate_trade(state, action) == []

    def test_wrong_phase(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.ATTACK,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("DEPLOY" in e for e in errors)

    def test_wrong_player(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
            current_player="P2",
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("P2" in e or "turn" in e.lower() for e in errors)

    def test_no_hand(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P2": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("no hand" in e.lower() for e in errors)

    def test_index_out_of_range_at_boundary(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 3), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("out of range" in e.lower() for e in errors)

    def test_index_out_of_range_negative(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, -1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("-1" in e for e in errors)

    def test_invalid_set(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, C_D)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("valid" in e.lower() and "set" in e.lower() for e in errors)

    def test_bonus_mismatch_claimed_when_none_exists(self):
        state = _make_state(
            owners={"A": "P2", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory="A")
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("bonus" in e.lower() for e in errors)

    def test_bonus_mismatch_claimed_wrong_territory(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory="B")
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("mismatch" in e.lower() for e in errors)

    def test_bonus_none_claimed_when_bonus_exists(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("mismatch" in e.lower() for e in errors)

    def test_duplicate_indices(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, I_B, I_C)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 0, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) >= 1
        assert any("valid" in e.lower() and "set" in e.lower() for e in errors)

    def test_empty_hand(self):
        state = _make_state(
            owners={"A": "P2", "B": "P2", "C": "P1"},
            player_hands={"P1": (I_A, I_B)},
            current_phase=Phase.DEPLOY,
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 2), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) == 1

    def test_multiple_errors_accumulated(self):
        state = _make_state(
            current_phase=Phase.ATTACK,
            current_player="P2",
            owners={"A": "P1", "B": "P1", "C": "P1"},
            player_hands={"P1": (I_A, C_D, I_C)},
        )
        action = TradeCardsAction(player="P1", card_indices=(0, 1, 5), bonus_territory=None)
        errors = validate_trade(state, action)
        assert len(errors) == 3


class TestValidateEndPhase:

    def test_valid_end_attack(self):
        state = _make_state(current_phase=Phase.ATTACK)
        action = EndPhaseAction(player="P1")
        assert validate_end_phase(state, action) == []

    def test_valid_end_fortify(self):
        state = _make_state(current_phase=Phase.FORTIFY)
        action = EndPhaseAction(player="P1")
        assert validate_end_phase(state, action) == []

    def test_invalid_end_deploy(self):
        state = _make_state(current_phase=Phase.DEPLOY)
        action = EndPhaseAction(player="P1")
        errors = validate_end_phase(state, action)
        assert len(errors) >= 1
        assert any("deploy" in e.lower() or "end" in e.lower() for e in errors)

    def test_invalid_end_game_over(self):
        state = _make_state(current_phase=Phase.GAME_OVER)
        action = EndPhaseAction(player="P1")
        errors = validate_end_phase(state, action)
        assert len(errors) >= 1

    def test_wrong_player(self):
        state = _make_state(
            current_phase=Phase.ATTACK,
            current_player="P2",
        )
        action = EndPhaseAction(player="P1")
        errors = validate_end_phase(state, action)
        assert len(errors) >= 1
        assert any("P2" in e or "turn" in e.lower() for e in errors)

    def test_multiple_errors_accumulated(self):
        state = _make_state(
            current_phase=Phase.DEPLOY,
            current_player="P2",
        )
        action = EndPhaseAction(player="P1")
        errors = validate_end_phase(state, action)
        assert len(errors) >= 2


class TestHasFriendlyPath:

    def test_adjacent_both_owned(self):
        state = _make_state(owners={"A": "P1", "B": "P1", "C": "P2"})
        assert has_friendly_path(state, "A", "B", "P1") is True

    def test_multihop_path(self):
        state = _make_state(owners={"A": "P1", "B": "P1", "C": "P1"})
        assert has_friendly_path(state, "A", "C", "P1") is True

    def test_blocked_by_enemy(self):
        state = _make_state(owners={"A": "P1", "B": "P2", "C": "P1"})
        assert has_friendly_path(state, "A", "C", "P1") is False

    def test_same_territory(self):
        state = _make_state(owners={"A": "P1", "B": "P2", "C": "P2"})
        assert has_friendly_path(state, "A", "A", "P1") is True

    def test_target_not_owned(self):
        state = _make_state(owners={"A": "P1", "B": "P2", "C": "P2"})
        assert has_friendly_path(state, "A", "B", "P1") is False

    def test_source_not_owned(self):
        state = _make_state(owners={"A": "P2", "B": "P1", "C": "P2"})
        assert has_friendly_path(state, "A", "B", "P1") is False

    def test_nonexistent_territory(self):
        state = _make_state()
        assert has_friendly_path(state, "X", "A", "P1") is False
        assert has_friendly_path(state, "A", "X", "P1") is False

    def test_both_not_owned(self):
        state = _make_state(owners={"A": "P2", "B": "P2", "C": "P2"})
        assert has_friendly_path(state, "A", "B", "P1") is False

    def test_same_territory_source_not_owned(self):
        state = _make_state(owners={"A": "P2", "B": "P1", "C": "P1"})
        assert has_friendly_path(state, "A", "A", "P1") is False

    def test_cycle_in_graph_still_finds_path(self):
        gm = GameMap.from_dict({
            "continents": {"Cont": {"bonus": 1, "territories": ["A", "B", "C", "D"]}},
            "territories": {
                "A": {"continent": "Cont", "adjacent": ["B", "C"]},
                "B": {"continent": "Cont", "adjacent": ["A", "D"]},
                "C": {"continent": "Cont", "adjacent": ["A", "D"]},
                "D": {"continent": "Cont", "adjacent": ["B", "C"]},
            },
        })
        state = _make_state(map=gm, owners={t: "P1" for t in gm.territories})
        assert has_friendly_path(state, "A", "D", "P1") is True

    def test_disconnected_friendly_subgraph(self):
        gm = GameMap.from_dict({
            "continents": {"Tiny": {"bonus": 1, "territories": ["A", "B", "C", "D"]}},
            "territories": {
                "A": {"continent": "Tiny", "adjacent": ["B", "D"]},
                "B": {"continent": "Tiny", "adjacent": ["A"]},
                "C": {"continent": "Tiny", "adjacent": ["D"]},
                "D": {"continent": "Tiny", "adjacent": ["C", "A"]},
            },
        })
        state = _make_state(owners={"A": "P1", "B": "P1", "C": "P1", "D": "P2"}, map=gm)
        assert has_friendly_path(state, "A", "C", "P1") is False

    def test_friendly_path_with_unowned_territory(self):
        state = _make_state(owners={"A": "P1", "C": "P1"})
        assert has_friendly_path(state, "A", "C", "P1") is False


class TestValidatorIntegration:

    def test_empty_errors_means_valid(self):
        state = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 4, "B": 1, "C": 1},
        )

        assert validate_deploy(state, DeployAction("P1", {"A": 3})) == []

        state_att = _make_state(current_phase=Phase.ATTACK)
        assert validate_end_phase(state_att, EndPhaseAction("P1")) == []

        state_for = _make_state(
            owners={"A": "P1", "B": "P1", "C": "P2"},
            armies={"A": 5, "B": 1, "C": 1},
            current_phase=Phase.FORTIFY,
        )
        assert validate_fortify(state_for, FortifyAction("P1", "A", "B", 2)) == []

    def test_phase_mismatch_does_not_crash_other_checks(self):
        state = _make_state(current_phase=Phase.ATTACK, current_player="P2")
        action = DeployAction(player="P1", allocations={"X": -5})
        errors = validate_deploy(state, action)
        assert isinstance(errors, list)
        assert len(errors) >= 4
        assert all(isinstance(e, str) for e in errors)

        action2 = AttackAction(player="P3", source="Y", target="Z", dice_count=5)
        errors2 = validate_attack(state, action2)
        assert isinstance(errors2, list)
        assert len(errors2) >= 4
        assert all(isinstance(e, str) for e in errors2)

    def test_validators_never_raise_on_expected_error_conditions(self):
        gm = _tiny_map()
        state = _make_state(map=gm)

        result = validate_deploy(state, DeployAction("P1", {"NonEx": 1}))
        assert isinstance(result, list)

        state_att = _make_state(map=gm, current_phase=Phase.ATTACK)
        result = validate_attack(state_att, AttackAction("P1", "NonEx", "B", 2))
        assert isinstance(result, list)

        state_fort = _make_state(map=gm, current_phase=Phase.FORTIFY)
        result = validate_fortify(state_fort, FortifyAction("P1", "NonX", "B", 2))
        assert isinstance(result, list)

        state_dep = _make_state(map=gm, current_phase=Phase.DEPLOY)
        result = validate_trade(state_dep, TradeCardsAction("P1", (0, 1, 2), None))
        assert isinstance(result, list)

        state_go = _make_state(map=gm, current_phase=Phase.GAME_OVER)
        result = validate_end_phase(state_go, EndPhaseAction("P1"))
        assert isinstance(result, list)
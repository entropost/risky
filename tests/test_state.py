from risky.engine import GameMap, GameState, Phase, Symbol, Card

def _tiny_map() -> GameMap:
    return GameMap.from_dict({
        "continents": {"TestCont": {"bonus": 1, "territories": ["A", "B"]}},
        "territories": {
            "A": {"continent": "TestCont", "adjacent": ["B"]},
            "B": {"continent": "TestCont", "adjacent": ["A"]},
        },
    })

def _make_state(
    map: GameMap | None = None,
    owners: dict[str, str] | None = None,
    armies: dict[str, int] | None = None,
    player_hands: dict[str, tuple[Card, ...]] | None = None,
    deck: tuple[Card, ...] | None = None,
    discards: tuple[Card, ...] | None = None,
    trade_in_count: int = 0,
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
    return GameState(
        map=gm, owners=owners, armies=armies,
        player_hands=player_hands if player_hands is not None else {},
        deck=deck if deck is not None else (),
        discards=discards if discards is not None else (),
        trade_in_count=trade_in_count, current_player=current_player,
        current_phase=current_phase,
        eliminated=eliminated if eliminated is not None else frozenset(),
        turn_number=turn_number, conquered_this_turn=conquered_this_turn,
    )

def test_phase_enum_values():
    assert Phase.DEPLOY.value == "deploy"
    assert Phase.ATTACK.value == "attack"
    assert Phase.FORTIFY.value == "fortify"
    assert Phase.GAME_OVER.value == "game_over"

def test_symbol_enum_values():
    assert Symbol.INFANTRY.value == "infantry"
    assert Symbol.CAVALRY.value == "cavalry"
    assert Symbol.ARTILLERY.value == "artillery"
    assert Symbol.WILD.value == "wild"

def test_card_creation():
    card = Card(territory="Alaska", symbol=Symbol.INFANTRY)
    assert card.territory == "Alaska"
    assert card.symbol == Symbol.INFANTRY
    wild = Card(territory=None, symbol=Symbol.WILD)
    assert wild.territory is None

def test_territory_owner():
    state = _make_state(owners={"A": "P1", "B": "P2"})
    assert state.territory_owner("A") == "P1"
    assert state.territory_owner("B") == "P2"

def test_player_territories():
    state = _make_state(owners={"A": "P1", "B": "P2"})
    assert state.player_territories("P1") == frozenset({"A"})
    assert state.player_territories("P2") == frozenset({"B"})

def test_territory_count():
    state = _make_state(owners={"A": "P1", "B": "P2"})
    assert state.territory_count("P1") == 1
    assert state.territory_count("P2") == 1
    state2 = _make_state(owners={"A": "P1", "B": "P1"})
    assert state2.territory_count("P1") == 2

def test_player_armies():
    state = _make_state(owners={"A": "P1", "B": "P2"}, armies={"A": 5, "B": 3})
    assert state.player_armies("P1") == 5
    assert state.player_armies("P2") == 3
    state2 = _make_state(owners={"A": "P1", "B": "P1"}, armies={"A": 5, "B": 3})
    assert state2.player_armies("P1") == 8

def test_continent_owner_full():
    state = _make_state(owners={"A": "P1", "B": "P1"})
    assert state.continent_owner("TestCont") == "P1"

def test_continent_owner_partial():
    state = _make_state(owners={"A": "P1", "B": "P2"})
    assert state.continent_owner("TestCont") is None

def test_continent_held_count():
    state = _make_state(owners={"A": "P1", "B": "P2"}, current_player="P1")
    assert state.continent_held_count("TestCont") == (1, 2)

def test_is_game_over_false():
    state = _make_state(owners={"A": "P1", "B": "P2"})
    assert state.is_game_over() is False

def test_is_game_over_true():
    state = _make_state(owners={"A": "P1", "B": "P1"}, eliminated=frozenset({"P2"}))
    assert state.is_game_over() is True

def test_winner_not_game_over():
    state = _make_state(owners={"A": "P1", "B": "P2"})
    assert state.winner() is None

def test_winner():
    state = _make_state(owners={"A": "P1", "B": "P1"}, eliminated=frozenset({"P2"}))
    assert state.winner() == "P1"

def test_copy_is_deep():
    state = _make_state(owners={"A": "P1", "B": "P1"}, armies={"A": 3, "B": 5})
    copied = state.copy()
    copied.owners["A"] = "P2"
    copied.armies["B"] = 99
    assert state.owners["A"] == "P1"
    assert state.armies["B"] == 5

def test_serialization_roundtrip():
    state = _make_state(owners={"A": "P1", "B": "P2"}, armies={"A": 3, "B": 5})
    d = state.to_dict()
    assert isinstance(d["map"], dict)
    assert d["owners"] == {"A": "P1", "B": "P2"}
    assert d["armies"] == {"A": 3, "B": 5}
    reloaded = GameState.from_dict(d)
    assert reloaded.owners == state.owners
    assert reloaded.armies == state.armies
    assert reloaded.current_player == state.current_player
    assert reloaded.current_phase == state.current_phase
    assert reloaded.turn_number == state.turn_number
    assert reloaded.conquered_this_turn == state.conquered_this_turn
    assert reloaded.trade_in_count == state.trade_in_count

def test_full_map_in_state():
    gm = GameMap.classic()
    owners = {t: "P1" for t in gm.territories}
    armies = {t: 1 for t in gm.territories}
    state = _make_state(map=gm, owners=owners, armies=armies)
    assert len(state.owners) == 42
    for t in gm.territories:
        assert t in state.owners
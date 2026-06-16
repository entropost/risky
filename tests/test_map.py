import pytest
from risky.engine import Territory, Continent, GameMap

@pytest.fixture
def tiny_map() -> GameMap:
    return GameMap.from_dict(
        {"continents": {"TinyCont": {"bonus": 1, "territories": ["A", "B", "C"]}},
          "territories":
          {
            "A": {"continent": "TinyCont", "adjacent": ["B"]},
            "B": {"continent": "TinyCont", "adjacent": ["A", "C"]},
            "C": {"continent": "TinyCont", "adjacent": ["B"]},
          }})

def test_validation_symmetry():
    with pytest.raises(ValueError, match="but neighbor does not"):
        GameMap.from_dict({"continents": {"X": {"bonus": 1, "territories": ["A", "B", "C"]}},
                           "territories": 
                           {
                               "A" : {"continent": "X", "adjacent": ["B"]},
                               "B" : {"continent": "X", "adjacent": ["C"]},
                               "C" : {"continent": "X", "adjacent": ["B"]},
                           }})

def test_validation_self_adjacency():
    with pytest.raises(ValueError, match="adjacent to itself"):
        GameMap.from_dict({"continents": {"X": {"bonus": 1, "territories": ["A", "B"]}},
                           "territories": 
                           {
                               "A" : {"continent": "X", "adjacent": ["B"]},
                               "B" : {"continent": "X", "adjacent": ["A", "B"]},
                           }})
        
def test_validation_missing_territory():
    with pytest.raises(ValueError, match="but continent does not"):
        GameMap.from_dict({"continents": {"X": {"bonus": 1, "territories": ["A"]}},
                           "territories": 
                           {
                               "A" : {"continent": "X", "adjacent": ["B"]},
                               "B" : {"continent": "X", "adjacent": ["A"]},
                           }})
        
## TODO: Add more validation tests

@pytest.fixture(scope="module")
def classic() -> GameMap:
    return GameMap.classic()

def test_classic_map_loads(classic: GameMap):
    assert classic is not None

def test_territory_count(classic: GameMap):
    assert len(classic.territories) == 42

def test_continent_count(classic: GameMap):
    assert len(classic.continents) == 6

def test_continent_bonuses(classic: GameMap):
    expected = {"North America": 5, "South America": 2, "Europe": 5,
                "Africa": 3, "Asia": 7, "Australia": 2}
    for name, bonus in expected.items():
        assert classic.continents[name].bonus == bonus


def test_adjacency_symmetry(classic: GameMap):
    for t_name, terr in classic.territories.items():
        for neighbor in terr.adjacent:
            assert t_name in classic.territories[neighbor].adjacent

def test_no_self_adjacency(classic: GameMap):
    for t_name, terr in classic.territories.items():
        assert t_name not in terr.adjacent

def test_are_adjacent(classic: GameMap):
    assert classic.are_adjacent("Alaska", "Kamchatka") is True
    assert classic.are_adjacent("Alaska", "Brazil") is False

def test_get_continent(classic: GameMap):
    assert classic.get_continent("Brazil").name == "South America"

def test_continent_membership(classic: GameMap):
    for t_name, terr in classic.territories.items():
        assert t_name in classic.continents[terr.continent].territories

def test_sea_lanes(classic: GameMap):
    assert classic.are_adjacent("North Africa", "Brazil")
    assert classic.are_adjacent("Alaska", "Kamchatka")
    assert classic.are_adjacent("Iceland", "Greenland")
    assert classic.are_adjacent("Indonesia", "Siam")
    assert classic.are_adjacent("Japan", "Kamchatka")

def test_contiguous_continent(classic: GameMap):
    for c_name, cont in classic.continents.items():
        start = next(iter(cont.territories))
        visited: set[str] = set()
        stack = [start]
        while stack:
            t = stack.pop()
            if t in visited:
                continue
            visited.add(t)
            for n in classic.territories[t].adjacent:
                if n in cont.territories and n not in visited:
                    stack.append(n)
        assert visited == cont.territories
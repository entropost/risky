from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
from importlib import resources

@dataclass(frozen=True)
class Territory:
    name: str
    continent: str
    adjacent: frozenset[str]

@dataclass(frozen=True)
class Continent:
    name: str
    territories: frozenset[str]
    bonus: int

@dataclass(frozen=True)
class GameMap:
    territories: dict[str, Territory]
    continents: dict[str, Continent]

    def __post_init__(self) -> None:
        errors : list[str] = []
        for c_name, cont in self.continents.items():
            for t_name in cont.territories:
                if t_name not in self.territories:
                    errors.append(f"Continent {c_name!r} lists non-existent territory {t_name!r}")
                elif c_name != self.territories[t_name].continent:
                    errors.append(f"Continent {c_name!r} lists territory {t_name!r}, but territory does not")
        
        for t_name, terr in self.territories.items():
            if terr.continent not in self.continents:
                errors.append(f"Territory {t_name!r} lists non-existent continent {terr.continent!r}")
            elif t_name not in self.continents[terr.continent].territories:
                errors.append(f"Territory {t_name!r} claims continent {terr.continent!r}, but continent does not")
            for neighbor in terr.adjacent:
                if neighbor not in self.territories:
                    errors.append(f"Territory {t_name!r} lists non-existent neighbor {neighbor!r}")
                elif t_name not in self.territories[neighbor].adjacent:
                    errors.append(f"Territory {t_name!r} claims neighbor {neighbor!r}, but neighbor does not")
            if t_name in terr.adjacent:
                errors.append(f"Territory {t_name!r} is adjacent to itself")
            if not terr.adjacent:
                errors.append(f"Territory {t_name!r} has no neighbor")
        if errors:
            raise ValueError("GameMap validation failed:\n" + "\n".join(f" - {e}" for e in errors))



    def get_continent(self, territory_name: str) -> Continent:
        return self.continents[self.territories[territory_name].continent]

    def are_adjacent(self, t1: str, t2: str) -> bool:
        return t2 in self.territories[t1].adjacent


    @staticmethod
    def from_dict(data: dict[str, Any]) -> GameMap:
        territories : dict[str, Territory] = {}
        continents : dict[str, Continent] = {}
        for name, info in data["territories"].items():
            territories[name] = Territory(name,
                                          info["continent"],
                                          frozenset(info["adjacent"]))
        for name, info in data["continents"].items():
            continents[name] = Continent(name,
                                         frozenset(info["territories"]),
                                         info["bonus"])
        return GameMap(territories, continents)
    
    @staticmethod
    def classic() -> GameMap:
        data = json.loads(resources.files("risky.data").joinpath("classic.json").read_text())
        return GameMap.from_dict(data)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "territories": {
                name: {"continent": t.continent, "adjacent": list(t.adjacent)}
                for name, t in self.territories.items()
            },
            "continents": {
                name: {"bonus": c.bonus, "territories": list(c.territories)}
                for name, c in self.continents.items()
            },
        }
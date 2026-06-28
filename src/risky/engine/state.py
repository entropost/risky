from __future__ import annotations


from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from risky.engine.map import GameMap


class Phase(Enum):
    DEPLOY = "deploy"
    ATTACK = "attack"
    FORTIFY = "fortify"
    GAME_OVER = "game_over"

class Symbol(Enum):
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARTILLERY = "artillery"
    WILD = "wild"

@dataclass(frozen=True)
class Card():
    territory : str | None
    symbol : Symbol

@dataclass(eq= False)
class GameState():
    map : GameMap
    owners : dict[str, str]
    armies : dict[str, int]
    player_hands : dict[str, tuple[Card, ...]]
    deck : tuple[Card, ...]
    discards : tuple[Card, ...]
    trade_in_counts : dict[str, int] = field(default_factory=dict)
    current_player : str = "P1"
    current_phase : Phase = Phase.DEPLOY
    eliminated : frozenset[str] = field(default_factory=frozenset)
    turn_number: int = 0
    conquered_this_turn : bool = False

    def copy(self) -> GameState:
        return GameState(
            map = self.map,
            owners = dict(self.owners),
            armies = dict(self.armies),
            player_hands = {p: tuple(h) for p, h in self.player_hands.items()},
            deck = self.deck,
            discards = self.discards,
            trade_in_counts = self.trade_in_counts,
            current_player = self.current_player,
            current_phase = self.current_phase,
            eliminated = self.eliminated,
            turn_number = self.turn_number,
            conquered_this_turn = self.conquered_this_turn,
        )
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GameState):
            return NotImplemented
        return (
            self.map is other.map
            and self.owners == other.owners
            and self.armies == other.armies
            and self.player_hands == other.player_hands
            and self.deck == other.deck
            and self.discards == other.discards
            and self.trade_in_counts == other.trade_in_counts
            and self.current_player == other.current_player
            and self.current_phase == other.current_phase
            and self.eliminated == other.eliminated
            and self.turn_number == other.turn_number
            and self.conquered_this_turn == other.conquered_this_turn
        )
    
    __hash__ = None # type: ignore[assignment]

    def territory_owner(self, name: str) -> str | None:
        return self.owners[name]
    
    def player_territories(self, player: str) -> frozenset[str]:
        return frozenset({t for t, o in self.owners.items() if o == player})
    
    def territory_count(self, player: str) -> int:
        return sum(1 for t, o in self.owners.items() if o == player)
    
    def continent_owner(self, continent_name: str) -> str | None:
        cont = self.map.continents[continent_name]
        owner = self.owners[next(iter(cont.territories))]
        if owner is None:
            return None
        for t in cont.territories:
            if self.owners[t] != owner:
                return None
        return owner
    
    def continent_held_count(self, continent_name: str) -> tuple[int, int]:
        """Return (territories held by current_player in continent, total in continent)."""
        cont = self.map.continents[continent_name]
        a, b = 0, 0
        for t in cont.territories:
            if self.owners[t] == self.current_player:
                a += 1
            b += 1
        return (a, b)
    
    def player_armies(self, player: str) -> int:
        res = 0
        for t, o in self.owners.items():
            if o == player:
                res += self.armies[t]
        return res
    
    #TODO: Verify the function logic; probably to be refactored in the future
    def is_game_over(self) -> bool:
        """Game ends when <= 1 player remains uneliminated."""
        active = {o for o in self.owners.values() if o not in self.eliminated}
        return len(active) <= 1
    
    def winner(self) -> str | None:
        if not self.is_game_over():
            return None
        active = {o for o in self.owners.values() if o not in self.eliminated}
        return next(iter(active)) if active else None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "map": self.map.to_dict(),
            "owners": dict(self.owners),
            "armies": dict(self.armies),
            "player_hands": {
                p: [{"territory": c.territory, "symbol": c.symbol.value} for c in hand]
                for p, hand in self.player_hands.items()
            },
            "deck": [{"territory": c.territory, "symbol": c.symbol.value} for c in self.deck],
            "discards": [{"territory": c.territory, "symbol": c.symbol.value} for c in self.discards],
            "trade_in_counts": self.trade_in_counts,
            "current_player": self.current_player,
            "current_phase": self.current_phase.value,
            "eliminated": list(self.eliminated),
            "turn_number": self.turn_number,
            "conquered_this_turn": self.conquered_this_turn,
        }
    
    @staticmethod
    def from_dict(data: dict[str, Any]) -> GameState:
        return GameState(
            map = GameMap.from_dict(data["map"]),
            owners = dict(data["owners"]),
            armies = dict(data["armies"]),
            player_hands ={
                p: tuple(
                    Card(territory=c["territory"], symbol=Symbol(c["symbol"]))
                    for c in cards
                )
                for p, cards in data["player_hands"].items()
            },
            deck=tuple(Card(territory=c["territory"], symbol=Symbol(c["symbol"])) for c in data["deck"]),
            discards=tuple(Card(territory=c["territory"], symbol=Symbol(c["symbol"])) for c in data["discards"]),
            trade_in_counts=data["trade_in_counts"],
            current_player=data["current_player"],
            current_phase=Phase(data["current_phase"]),
            eliminated=frozenset(data["eliminated"]),
            turn_number=data["turn_number"],
            conquered_this_turn=data["conquered_this_turn"],
        )
    

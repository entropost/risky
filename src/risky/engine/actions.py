from __future__ import annotations

from dataclasses import dataclass
from typing import Union

@dataclass(frozen=True)
class DeployAction():
    player: str
    allocations : dict[str, int]

@dataclass(frozen=True)
class AttackAction():
    player: str
    source: str
    target: str
    dice_count: int

@dataclass(frozen=True)
class FortifyAction():
    player: str
    source: str
    target: str
    army_count: int

@dataclass(frozen=True)
class TradeCardsAction():
    player: str
    card_indices: tuple[int, int, int]
    bonus_territory: str | None

@dataclass(frozen=True)
class EndPhaseAction():
    player: str

Action = Union[DeployAction, AttackAction, FortifyAction, TradeCardsAction, EndPhaseAction]

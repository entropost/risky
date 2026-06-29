from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from math import ceil

from risky.engine.state import Card, Symbol, GameState
from risky.engine.map import GameMap

class SetKind(Enum):
    THREE_INFANTRY = "three_infantry"
    THREE_CAVALRY = "three_cavalry"
    THREE_ARTILLERY = "three_artillery"
    THREE_WILD = "three_wild"
    ONE_OF_EACH = "one_of_each"

@dataclass(frozen=True)
class TradeSet:
    indices: tuple[int, int, int]
    kind: SetKind

DEFAULT_FIXED_VALUES: dict[SetKind, int] = {
    SetKind.THREE_INFANTRY: 4,
    SetKind.THREE_CAVALRY: 6,
    SetKind.THREE_ARTILLERY: 8,
    SetKind.THREE_WILD: 10,
    SetKind.ONE_OF_EACH: 10,
}

def create_deck(map: GameMap, wild_count: int = 2) -> tuple[Card, ...]:
    names = sorted(map.territories.keys())
    N = len(names)

    infantry_count = ceil(N / 3)
    cavalry_count = ceil((N - infantry_count) / 2)
    cards = []

    for i in range(N):
        if i < infantry_count:
            cards.append(Card(territory=names[i], symbol=Symbol.INFANTRY))
        elif i < infantry_count + cavalry_count:
            cards.append(Card(territory=names[i], symbol=Symbol.CAVALRY))
        else:
            cards.append(Card(territory=names[i], symbol=Symbol.ARTILLERY))
    
    for _ in range(wild_count):
        cards.append(Card(territory=None, symbol=Symbol.WILD))

    return tuple(cards)

def shuffle(deck: tuple[Card, ...], rng: random.Random) -> tuple[Card, ...]:
    if len(deck) <= 1:
        return deck
    
    items = list(deck)
    for i in range(len(items)-1, 0, -1):
        j = rng.randint(0, i)
        items[i], items[j] = items[j], items[i]
    
    return tuple(items)

def draw(deck: tuple[Card, ...], discards: tuple[Card, ...], rng: random.Random) \
                -> tuple[Card | None, tuple[Card, ...], tuple[Card, ...]]:
    if len(deck) < 1:
        if len(discards) < 1:
            return (None, (), ())
        deck = shuffle(discards, rng)
        discards = ()
    card = deck[-1]
    new_deck = deck[:-1]
    return (card, new_deck, discards)

def discard_to_pile(cards: tuple[Card, ...], discards: tuple[Card, ...]) -> tuple[Card, ...]:
    return discards + cards

def classify_triple(hand: tuple[Card, ...], i: int, j: int, k: int, values: dict[SetKind, int]) -> SetKind | None:
    counts = {s: 0 for s in Symbol}

    for idx in (i, j, k):
        card = hand[idx]
        counts[card.symbol] += 1
    
    ni = counts[Symbol.INFANTRY]
    nc = counts[Symbol.CAVALRY]
    na = counts[Symbol.ARTILLERY]
    nw = counts[Symbol.WILD]

    if nw == 3:
        return SetKind.THREE_WILD
    
    if nw == 0:
        if ni == 3: return SetKind.THREE_INFANTRY
        if nc == 3: return SetKind.THREE_CAVALRY
        if na == 3: return SetKind.THREE_ARTILLERY
        if ni == 1 and nc == 1 and na == 1: return SetKind.ONE_OF_EACH
        return None
    
    if nw == 1:
        if ni == 2: return SetKind.THREE_INFANTRY
        if nc == 2: return SetKind.THREE_CAVALRY
        if na == 2: return SetKind.THREE_ARTILLERY
        if (ni == 1 and nc == 1) or (ni == 1 and na == 1) or (nc == 1 and na == 1): return SetKind.ONE_OF_EACH
        return None
    
    possible = []
    if ni == 1: possible.append(SetKind.THREE_INFANTRY)
    if nc == 1: possible.append(SetKind.THREE_CAVALRY)
    if na == 1: possible.append(SetKind.THREE_ARTILLERY)
    possible.append(SetKind.ONE_OF_EACH)

    return max(possible, key=lambda k: fixed_trade_value(k, values))

def find_valid_sets(hand: tuple[Card, ...], values: dict[SetKind, int] | None = None) -> list[TradeSet]:
    if values is None:
        values = DEFAULT_FIXED_VALUES
    if len(hand) < 3:
        return []
    
    result = []
    n = len(hand)
    for i in range(0, n - 2):
        for j in range(i + 1, n - 1):
            for k in range(j + 1, n):
                kind = classify_triple(hand, i, j, k, values)
                if kind is not None:
                    result.append(TradeSet(indices=(i, j, k), kind=kind))
    return result

def has_valid_set(hand: tuple[Card, ...]) -> bool:
    return len(find_valid_sets(hand)) > 0

def must_trade(hand: tuple[Card, ...]) -> bool:
    return len(hand) >= 5

def fixed_trade_value(kind: SetKind, values: dict[SetKind, int] | None = None) -> int:
    if values is None:
        values = DEFAULT_FIXED_VALUES
    return values[kind]

def territory_bonus(indices: tuple[int, int, int], hand: tuple[Card, ...], state: GameState, player: str) \
                    -> tuple[int, str | None]:
    for idx in sorted(indices):
        card = hand[idx]
        if card.territory is None:
            continue
        elif state.territory_owner(card.territory) == player:
            return (2, card.territory)
    return (0, None)
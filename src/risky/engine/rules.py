from collections import deque

from risky.engine.state import GameState, Phase
from risky.engine.cards import find_valid_sets, territory_bonus
from risky.engine.actions import Action, DeployAction, AttackAction, FortifyAction, TradeCardsAction, EndPhaseAction


def has_friendly_path(state: GameState, source: str, target: str, player: str) -> bool:
    if state.territory_owner(source) != player or state.territory_owner(target) != player:
        return False
    if source == target:
        return True

    vis = {source}
    frontier = deque([source])

    while frontier:
        current = frontier.popleft()
        for neighbor in state.map.territories[current].adjacent:
            if neighbor == target:
                return True
            if neighbor not in vis and state.territory_owner(neighbor) == player:
                vis.add(neighbor)
                frontier.append(neighbor)
    return False


def validate_deploy(state: GameState, action: DeployAction) -> list[str]:
    errors: list[str] = []

    if state.current_phase != Phase.DEPLOY:
        errors.append("Deploy actions are only allowed during the DEPLOY phase")

    if action.player != state.current_player:
        errors.append(f"It is {state.current_player}'s turn, not {action.player}'s")

    if not action.allocations:
        errors.append("Must deploy at least one army")

    for territory_name, count in action.allocations.items():
        owner = state.territory_owner(territory_name)
        if owner is None:
            errors.append(f"Territory '{territory_name}' does not exist")
        elif owner != action.player:
            errors.append(f"Territory '{territory_name}' is not owned by {action.player}")
        if count < 1:
            errors.append(f"Must place at least 1 army on '{territory_name}' (got {count})")

    return errors

def validate_attack(state: GameState, action: AttackAction) -> list[str]:
    errors: list[str] = []

    if state.current_phase != Phase.ATTACK:
        errors.append("Attack actions are only allowed during the ATTACK phase")

    if action.player != state.current_player:
        errors.append(f"It is {state.current_player}'s turn, not {action.player}'s")

    if action.dice_count not in {1, 2, 3}:
        errors.append(f"Dice count must be 1, 2, or 3 (got {action.dice_count})")

    source_owner = state.territory_owner(action.source)
    if source_owner is None:
        errors.append(f"Source territory '{action.source}' does not exist")
    elif source_owner != action.player:
        errors.append(f"Source territory '{action.source}' is not owned by {action.player}")

    target_owner = state.territory_owner(action.target)
    if target_owner is None:
        errors.append(f"Target territory '{action.target} does not exist'")
    if target_owner == action.player:
        errors.append(f"Target territory '{action.target}' must be owned by another player")

    if source_owner == action.player and target_owner is not None and target_owner != action.player:
        if not state.map.are_adjacent(action.source, action.target):
            errors.append(f"'{action.source}' and '{action.target}' are not adjacent")

        if action.source in state.armies:
            source_armies = state.armies[action.source]
            if source_armies < 2:
                errors.append(f"Source '{action.source}' must have at least 2 armies to attack")

            elif source_armies - 1 < action.dice_count:
                errors.append(f"Cannot roll {action.dice_count} dice from '{action.source}'; must leave at least 1 army after the attack")

    return errors


def validate_fortify(state: GameState, action: FortifyAction) -> list[str]:
    errors: list[str] = []

    if state.current_phase != Phase.FORTIFY:
        errors.append(f"Fortify actions are only allowed during the FORTIFY phase")

    if action.player != state.current_player:
        errors.append(f"It is {state.current_player}'s turn, not {action.player}'s")

    source_owner = None
    target_owner = None

    if action.source == action.target:
        errors.append(f"Source and target territories must be different")

    else:
        source_owner = state.territory_owner(action.source)
        if source_owner is None:
            errors.append(f"Source territory '{action.source}' does not exist")
        elif source_owner != action.player:
            errors.append(f"Source territory '{action.source}' is not owned by {action.player}")

        target_owner = state.territory_owner(action.target)
        if target_owner is None:
            errors.append(f"Target territory '{action.target}' does not exist")
        elif target_owner != action.player:
            errors.append(f"Target territory '{action.target}' is not owned by {action.player}")

    if action.army_count < 1:
        errors.append(f"Must transfer at least 1 army (got {action.army_count})")

    if source_owner == action.player and action.source in state.armies:
        source_armies = state.armies[action.source]
        if action.army_count >= source_armies:
            errors.append(f"Cannot transfer {action.army_count} from '{action.source}'; must leave at least 1 army behind (has {source_armies})s")

    if not errors:
        if not has_friendly_path(state, action.source, action.target, action.player):
            errors.append(f"No friendly path from '{action.source}' to '{action.target}' through territories owned by {action.player}")

    return errors


def validate_trade(state: GameState, action: TradeCardsAction) -> list[str]:
    errors: list[str] = []

    if state.current_phase != Phase.DEPLOY:
        errors.append("Trade actions are only allowed during the DEPLOY phase")

    if state.current_player != action.player:
        errors.append(f"It is {state.current_player}'s turn, not {action.player}'s")

    hand = state.player_hands.get(action.player)
    if hand is None:
        errors.append(f"Player '{action.player}' has no hand")
        return errors

    for idx in action.card_indices:
        if idx < 0 or idx >= len(hand):
            errors.append(f"Card index {idx} is out of range (hand has {len(hand)} cards)")

    if not errors:
        valid_sets = find_valid_sets(hand)
        found = any(ts.indices == action.card_indices for ts in valid_sets)
        if not found:
            errors.append(f"Cards at indices {action.card_indices} do not form a valid trade set")

    if not errors:
        _, actual_bonus = territory_bonus(action.card_indices, hand, state, action.player)

        if action.bonus_territory != actual_bonus:
            errors.append(f"Bonus territory mismatch: claimed {action.bonus_territory!r}, actual {actual_bonus!r}")

    return errors

def validate_end_phase(state: GameState, action: EndPhaseAction) -> list[str]:
    errors: list[str] = []

    if state.current_phase not in {Phase.ATTACK, Phase.FORTIFY}:
        errors.append(f"Cannot end the {state.current_phase.value} phase")

    if action.player != state.current_player:
        errors.append(f"It is {state.current_player}'s turn, not {action.player}'s")

    return errors
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from des_core.automata import DFA, State


class BeliefDeadlockKind(Enum):
    ROBUST_NONDEADLOCK = "robust-nondeadlock"
    POSSIBLE_DEADLOCK = "possible-deadlock"
    CERTAIN_DEADLOCK = "certain-deadlock"


@dataclass(frozen=True)
class BeliefDeadlockStatus:
    kind: BeliefDeadlockKind
    deadlocked_states: frozenset[State]
    nondeadlocked_states: frozenset[State]

    @property
    def possible_deadlock(self) -> bool:
        return bool(self.deadlocked_states)

    @property
    def certain_deadlock(self) -> bool:
        return bool(self.deadlocked_states) and not self.nondeadlocked_states

    @property
    def robust_nondeadlock(self) -> bool:
        return not self.deadlocked_states


def is_concrete_deadlock(plant: DFA, state: State) -> bool:
    return not plant.enabled_targets(state)


def classify_belief_deadlock(
    plant: DFA,
    closed_belief: frozenset[State],
) -> BeliefDeadlockStatus:
    deadlocked = frozenset(state for state in closed_belief if is_concrete_deadlock(plant, state))
    nondeadlocked = frozenset(state for state in closed_belief if state not in deadlocked)

    if deadlocked and not nondeadlocked:
        kind = BeliefDeadlockKind.CERTAIN_DEADLOCK
    elif deadlocked:
        kind = BeliefDeadlockKind.POSSIBLE_DEADLOCK
    else:
        kind = BeliefDeadlockKind.ROBUST_NONDEADLOCK

    return BeliefDeadlockStatus(
        kind=kind,
        deadlocked_states=deadlocked,
        nondeadlocked_states=nondeadlocked,
    )

from __future__ import annotations

from dataclasses import dataclass

from des_core.automata import DFA, Event, State
from des_core.deadlock_semantics import classify_belief_deadlock
from des_core.partial_observation import observable_successors


Belief = frozenset[State]
IBTSTransition = tuple[Belief, Event, Belief]


@dataclass(frozen=True)
class PruningResult:
    retained_beliefs: frozenset[Belief]
    retained_transitions: frozenset[IBTSTransition]
    deleted_beliefs: frozenset[Belief]
    newly_deleted: frozenset[Belief]


def classify_pruning_tag(plant: DFA, belief: Belief) -> str:
    """Return the pruning-aware Y/N tag for a closed belief.

    The paper's Y case is interpreted as non-deadlock for every concrete state
    in the belief, i.e. every possible state has at least one enabled successor.
    """

    status = classify_belief_deadlock(plant, belief)

    if status.possible_deadlock:
        return "N"

    return "Y"


def is_closed_after_pruning(
    plant: DFA,
    observable: frozenset[Event],
    belief: Belief,
    beliefs: set[Belief] | frozenset[Belief],
    transitions: set[IBTSTransition] | frozenset[IBTSTransition],
    deleted_beliefs: set[Belief] | frozenset[Belief],
) -> bool:
    """Check Definition 5 plus the pruning-aware successor case."""

    if belief in deleted_beliefs:
        return True

    known_transition_keys = {
        (source, event)
        for source, event, target in transitions
        if source in beliefs and target in beliefs
    }

    for successor in observable_successors(plant, belief, observable):
        if (belief, successor.event) in known_transition_keys:
            continue

        if successor.closed_belief in deleted_beliefs:
            continue

        return False

    return True


def prune_deadlock_branches(
    plant: DFA,
    observable: frozenset[Event],
    beliefs: set[Belief] | frozenset[Belief],
    transitions: set[IBTSTransition] | frozenset[IBTSTransition],
    deleted_beliefs: set[Belief] | frozenset[Belief] | None=None,
) -> PruningResult:
    """Prune closed deadlock and backward-losing belief branches.

    This is intentionally a separate module so the existing exploration code can
    keep constructing limited-lookahead fragments while pruning is applied as an additional
    fixed-point pass.
    """

    retained = set(beliefs)
    retained_transitions = set(transitions)
    deleted = set(deleted_beliefs or set())
    newly_deleted: set[Belief] = set()

    changed = True

    while changed:
        changed = False

        for belief in sorted(retained, key=_belief_sort_key):
            if not is_closed_after_pruning(
                plant,
                observable,
                belief,
                retained,
                retained_transitions,
                deleted,
            ):
                continue

            if _is_prunable(plant, observable, belief, retained_transitions, deleted):
                retained.remove(belief)
                deleted.add(belief)
                newly_deleted.add(belief)
                retained_transitions = {
                    transition
                    for transition in retained_transitions
                    if transition[0] != belief and transition[2] != belief
                }
                changed = True

                break

    return PruningResult(
        retained_beliefs=frozenset(retained),
        retained_transitions=frozenset(retained_transitions),
        deleted_beliefs=frozenset(deleted),
        newly_deleted=frozenset(newly_deleted),
    )


def _is_prunable(
    plant: DFA,
    observable: frozenset[Event],
    belief: Belief,
    transitions: set[IBTSTransition],
    deleted_beliefs: set[Belief],
) -> bool:
    if classify_pruning_tag(plant, belief) == "N":
        return True

    successors = observable_successors(plant, belief, observable)

    if not successors:
        return False

    retained_successors = {
        target
        for source, _event, target in transitions
        if source == belief and target not in deleted_beliefs
    }

    return not retained_successors


def _belief_sort_key(belief: Belief) -> tuple[str, ...]:
    return tuple(sorted(belief))

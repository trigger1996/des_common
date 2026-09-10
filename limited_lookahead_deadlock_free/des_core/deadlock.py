from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from des_core.automata import DFA, State
from des_core.deadlock_semantics import classify_belief_deadlock
from des_core.observer import ObservationTag, tagged_belief_name
from des_core.partial_observation import observable_successors
from des_core.pruning import Belief, IBTSTransition, classify_pruning_tag, prune_deadlock_branches


@dataclass(frozen=True)
class DeadlockSnapshot:
    title: str
    known_nodes: frozenset[State]
    known_edges: frozenset[tuple[State, State, str]]
    frontier: frozenset[State]
    nondeadlock: frozenset[State]
    deadlock: frozenset[State]


@dataclass(frozen=True)
class PartialObservationSnapshot:
    title: str
    known_nodes: frozenset[State]
    known_edges: frozenset[tuple[State, State, str]]
    belief: frozenset[State]
    observed_trace: tuple[str, ...]
    nondeadlock: frozenset[State]
    deadlock: frozenset[State]
    possible_deadlock_states: frozenset[State]
    robust_nondeadlock: bool
    possible_deadlock: bool
    certain_deadlock: bool


@dataclass(frozen=True)
class BeliefStateSynthesisSnapshot:
    title: str
    known_nodes: frozenset[State]
    known_edges: frozenset[tuple[State, State, str, str]]
    current: State | None
    frontier: frozenset[State]
    yes: frozenset[State]
    no: frozenset[State]
    unknown: frozenset[State]
    closed_beliefs: frozenset[State]
    raw_beliefs: frozenset[State]
    deadlock: frozenset[State]
    layout_aliases: tuple[tuple[State, State], ...]
    faded_nodes: frozenset[State] = field(default_factory=frozenset)
    faded_edges: frozenset[tuple[State, State, str, str]] = field(default_factory=frozenset)
    layout_style: str = "default"
    label_style: str = "full"


def compute_deadlock_status(
    known_nodes: set[State],
    known_edges: set[tuple[State, State, str]],
) -> tuple[set[State], set[State]]:
    """Classify known states by whether at least one outgoing transition is known."""

    outgoing_sources = {source for source, _target, _event in known_edges}
    nondeadlock = known_nodes & outgoing_sources
    deadlock = known_nodes - nondeadlock
    return nondeadlock, deadlock


def make_partial_observation_snapshots(
    plant: DFA,
    observable: frozenset[str],
) -> list[PartialObservationSnapshot]:
    """Explore the original plant on the fly under partial observation."""

    known_nodes: set[State] = {plant.initial}
    known_edges: set[tuple[State, State, str]] = set()
    snapshots: list[PartialObservationSnapshot] = []
    visited: set[frozenset[State]] = set()
    frontier: deque[tuple[frozenset[State], tuple[str, ...]]] = deque()

    def capture(title: str, belief: frozenset[State], trace: tuple[str, ...]) -> None:
        nondeadlock, deadlock = compute_deadlock_status(known_nodes, known_edges)
        belief_status = classify_belief_deadlock(plant, belief)
        snapshots.append(
            PartialObservationSnapshot(
                title=title,
                known_nodes=frozenset(known_nodes),
                known_edges=frozenset(known_edges),
                belief=belief,
                observed_trace=trace,
                nondeadlock=frozenset(nondeadlock),
                deadlock=frozenset(deadlock),
                possible_deadlock_states=belief_status.deadlocked_states,
                robust_nondeadlock=belief_status.robust_nondeadlock,
                possible_deadlock=belief_status.possible_deadlock,
                certain_deadlock=belief_status.certain_deadlock,
            )
        )

    def close_unobservable(seeds: set[State], belief: frozenset[State], trace: tuple[str, ...]) -> frozenset[State]:
        closure = set(seeds)
        queue: deque[State] = deque(seeds)
        while queue:
            source = queue.popleft()
            known_nodes.add(source)
            for event, target in plant.enabled(source):
                if event in observable:
                    continue
                known_nodes.add(target)
                known_edges.add((source, target, event))
                if target not in closure:
                    closure.add(target)
                    queue.append(target)
                    capture(f"unobservable closure adds {source} --{event}--> {target}", frozenset(closure), trace)
        return frozenset(closure)

    initial_belief = close_unobservable({plant.initial}, frozenset({plant.initial}), ())
    capture(f"initial belief {_belief_label(initial_belief)}", initial_belief, ())
    frontier.append((initial_belief, ()))

    while frontier:
        belief, trace = frontier.popleft()
        if belief in visited:
            continue
        visited.add(belief)

        successors = observable_successors(plant, belief, observable)
        if not successors:
            capture(f"no observable successor from belief {_belief_label(belief)}", belief, trace)
            continue

        for successor in successors:
            targets: set[State] = set()
            for state in sorted(belief):
                for enabled_event, target in plant.enabled(state):
                    if enabled_event != successor.event:
                        continue
                    known_nodes.add(state)
                    known_nodes.add(target)
                    known_edges.add((state, target, successor.event))
                    targets.add(target)
                    capture(f"observe {successor.event}: discover {state} --{successor.event}--> {target}", belief, trace)

            next_trace = (*trace, successor.event)
            next_belief = close_unobservable(targets, belief, next_trace)
            capture(f"after observing {successor.event}: belief {_belief_label(next_belief)}", next_belief, next_trace)
            if next_belief not in visited and next_belief not in [item[0] for item in frontier]:
                frontier.append((next_belief, next_trace))

    return snapshots


def make_belief_state_synthesis_snapshots(
    plant: DFA,
    observable: frozenset[str],
) -> list[BeliefStateSynthesisSnapshot]:
    """Build tagged observer snapshots with states i = (X, tag).

    The tag is dynamic:
    U means the belief has been discovered but has not been expanded yet.
    Y means every plant state in the closed belief has at least one enabled event.
    N means the belief contains at least one concrete deadlock state.
    """

    known_nodes: set[State] = set()
    known_edges: set[tuple[State, State, str, str]] = set()
    ibts_beliefs: set[Belief] = set()
    ibts_transitions: set[IBTSTransition] = set()
    deleted_beliefs: set[Belief] = set()
    label_to_belief: dict[State, frozenset[State]] = {}
    raw_beliefs: set[State] = set()
    closed_beliefs: set[State] = set()
    belief_tags: dict[frozenset[State], ObservationTag] = {}
    layout_aliases: list[tuple[State, State]] = []
    snapshots: list[BeliefStateSynthesisSnapshot] = []
    visited: set[frozenset[State]] = set()
    frontier: deque[tuple[frozenset[State], tuple[str, ...]]] = deque()

    def tag_for(belief: frozenset[State]) -> ObservationTag:
        return belief_tags.get(belief, ObservationTag.UNKNOWN)

    def semantic_tag(belief: frozenset[State]) -> ObservationTag:
        if classify_pruning_tag(plant, belief) == "N":
            return ObservationTag.NO
        return ObservationTag.YES

    def remember(belief: frozenset[State], raw: bool, tag: ObservationTag | None = None) -> State:
        if belief in deleted_beliefs:
            return _tagged_belief_label(belief, ObservationTag.NO)

        if tag is not None:
            belief_tags[belief] = tag
        elif belief not in belief_tags:
            belief_tags[belief] = ObservationTag.UNKNOWN

        label = _tagged_belief_label(belief, tag_for(belief))
        known_nodes.add(label)
        label_to_belief[label] = belief
        if raw:
            raw_beliefs.add(label)
        else:
            closed_beliefs.add(label)
            ibts_beliefs.add(belief)
        return label

    def close_unobservable(seeds: frozenset[State]) -> frozenset[State]:
        closure = set(seeds)
        queue: deque[State] = deque(seeds)
        while queue:
            source = queue.popleft()
            for event, target in plant.enabled(source):
                if event in observable or target in closure:
                    continue
                closure.add(target)
                queue.append(target)
        return frozenset(closure)

    def certain_deadlocks() -> set[State]:
        return {
            label
            for label, belief in label_to_belief.items()
            if belief and all(not plant.enabled_targets(state) for state in belief)
        }

    def labels_with_tag(tag: ObservationTag) -> set[State]:
        return {
            label
            for belief, belief_tag in belief_tags.items()
            for label in [_tagged_belief_label(belief, belief_tag)]
            if belief_tag == tag
            if label in known_nodes
        }

    def relabel_belief(belief: frozenset[State], tag: ObservationTag) -> State:
        if belief in deleted_beliefs:
            return _tagged_belief_label(belief, ObservationTag.NO)

        old_label = _tagged_belief_label(belief, tag_for(belief))
        new_label = _tagged_belief_label(belief, tag)
        if old_label == new_label:
            return new_label

        belief_tags[belief] = tag
        if old_label in known_nodes:
            known_nodes.remove(old_label)
            known_nodes.add(new_label)
        if old_label in raw_beliefs:
            raw_beliefs.remove(old_label)
            raw_beliefs.add(new_label)
        if old_label in closed_beliefs:
            closed_beliefs.remove(old_label)
            closed_beliefs.add(new_label)
        label_to_belief.pop(old_label, None)
        label_to_belief[new_label] = belief

        updated_edges = set()
        for source, target, event, kind in known_edges:
            updated_edges.add(
                (
                    new_label if source == old_label else source,
                    new_label if target == old_label else target,
                    event,
                    kind,
                )
            )
        known_edges.clear()
        known_edges.update(updated_edges)
        layout_aliases.append((old_label, new_label))
        return new_label

    def add_ibts_transition(source: Belief, event: str, target: Belief) -> None:
        if source in deleted_beliefs or target in deleted_beliefs:
            return
        ibts_transitions.add((source, event, target))

    def apply_pruning() -> set[Belief]:
        nonlocal ibts_beliefs, ibts_transitions, deleted_beliefs, frontier

        result = prune_deadlock_branches(
            plant=plant,
            observable=observable,
            beliefs=ibts_beliefs,
            transitions=ibts_transitions,
            deleted_beliefs=deleted_beliefs,
        )
        if not result.newly_deleted:
            return set()

        ibts_beliefs = set(result.retained_beliefs)
        ibts_transitions = set(result.retained_transitions)
        deleted_beliefs = set(result.deleted_beliefs)
        deleted_labels = {
            _tagged_belief_label(belief, tag)
            for belief in result.newly_deleted
            for tag in ObservationTag
        }
        known_nodes.difference_update(deleted_labels)
        raw_beliefs.difference_update(deleted_labels)
        closed_beliefs.difference_update(deleted_labels)
        for label in deleted_labels:
            label_to_belief.pop(label, None)
        removed_edges = {
            edge for edge in known_edges if edge[0] in deleted_labels or edge[1] in deleted_labels
        }
        known_edges.difference_update(removed_edges)
        frontier = deque(item for item in frontier if item[0] not in deleted_beliefs)
        remove_unreachable_retained_beliefs()
        return set(result.newly_deleted)

    def remove_unreachable_retained_beliefs() -> None:
        nonlocal ibts_beliefs, ibts_transitions, frontier

        if initial_belief in deleted_beliefs or initial_belief not in ibts_beliefs:
            reachable: set[Belief] = set()
        else:
            reachable = {initial_belief}
            changed = True
            while changed:
                changed = False
                for source, _event, target in ibts_transitions:
                    if source not in reachable or target in reachable:
                        continue
                    reachable.add(target)
                    changed = True

        unreachable = set(ibts_beliefs) - reachable
        if not unreachable:
            return

        ibts_beliefs.difference_update(unreachable)
        ibts_transitions = {
            transition
            for transition in ibts_transitions
            if transition[0] not in unreachable and transition[2] not in unreachable
        }

        unreachable_labels = {
            _tagged_belief_label(belief, tag)
            for belief in unreachable
            for tag in ObservationTag
        }
        known_nodes.difference_update(unreachable_labels)
        raw_beliefs.difference_update(unreachable_labels)
        closed_beliefs.difference_update(unreachable_labels)
        for label in unreachable_labels:
            label_to_belief.pop(label, None)
        for belief in unreachable:
            belief_tags.pop(belief, None)
        removed_unreachable_edges = {
            edge for edge in known_edges if edge[0] in unreachable_labels or edge[1] in unreachable_labels
        }
        known_edges.difference_update(removed_unreachable_edges)
        frontier = deque(item for item in frontier if item[0] not in unreachable)

    def preview_pruning() -> set[Belief]:
        result = prune_deadlock_branches(
            plant=plant,
            observable=observable,
            beliefs=ibts_beliefs,
            transitions=ibts_transitions,
            deleted_beliefs=deleted_beliefs,
        )
        return set(result.newly_deleted)

    def describe_deleted(deleted_now: set[Belief]) -> str:
        deleted_names = ", ".join(_belief_label(belief) for belief in sorted(deleted_now, key=lambda item: tuple(sorted(item))))
        return f"prune next: {deleted_names}"

    def capture(title: str, current: State | None) -> None:
        snapshots.append(
            BeliefStateSynthesisSnapshot(
                title=title,
                known_nodes=frozenset(known_nodes),
                known_edges=frozenset(known_edges),
                current=current,
                frontier=frozenset(_tagged_belief_label(item[0], tag_for(item[0])) for item in frontier),
                yes=frozenset(labels_with_tag(ObservationTag.YES)),
                no=frozenset(labels_with_tag(ObservationTag.NO)),
                unknown=frozenset(labels_with_tag(ObservationTag.UNKNOWN)),
                closed_beliefs=frozenset(closed_beliefs),
                raw_beliefs=frozenset(raw_beliefs),
                deadlock=frozenset(certain_deadlocks()),
                layout_aliases=tuple(layout_aliases),
            )
        )

    initial_raw = frozenset({plant.initial})
    initial_raw_label = remember(initial_raw, raw=True, tag=ObservationTag.UNKNOWN)

    initial_belief = close_unobservable(initial_raw)
    initial_label = remember(initial_belief, raw=False, tag=ObservationTag.UNKNOWN)
    if initial_belief != initial_raw:
        known_nodes.discard(initial_raw_label)
        raw_beliefs.discard(initial_raw_label)
        layout_aliases.append((initial_raw_label, initial_label))

    frontier.append((initial_belief, ()))
    capture(f"initial frontier starts with {initial_label}", initial_label)

    loop_index = 0
    while frontier:
        belief, trace = frontier.popleft()
        if belief in deleted_beliefs:
            continue
        if belief in visited:
            continue
        visited.add(belief)
        loop_index += 1
        loop_notes: list[str] = []
        source_label = remember(belief, raw=False)

        source_label = relabel_belief(belief, semantic_tag(belief))
        loop_notes.append(f"classified as {source_label.rsplit(':', 1)[-1]}")
        pruning_preview = preview_pruning()
        if pruning_preview:
            loop_notes.append(describe_deleted(pruning_preview))
            capture(f"loop {loop_index}: expand {source_label}; " + "; ".join(loop_notes), source_label)
            apply_pruning()
            continue

        successors = observable_successors(plant, belief, observable)
        if not successors:
            loop_notes.append("no observable successor")
            pruning_preview = preview_pruning()
            if pruning_preview:
                loop_notes.append(describe_deleted(pruning_preview))
            capture(f"loop {loop_index}: expand {source_label}; " + "; ".join(loop_notes), source_label)
            apply_pruning()
            continue

        for successor in successors:
            if belief in deleted_beliefs:
                break

            targets = successor.raw_targets
            next_trace = (*trace, successor.event)
            next_belief = successor.closed_belief
            if next_belief in deleted_beliefs:
                loop_notes.append(f"{successor.event}->pruned {_belief_label(next_belief)}")
                continue

            next_label = _tagged_belief_label(next_belief, tag_for(next_belief))
            target_already_known = next_belief in ibts_beliefs
            if target_already_known:
                retained_target_label = _tagged_belief_label(next_belief, tag_for(next_belief))
                add_ibts_transition(belief, successor.event, next_belief)
                known_edges.add((source_label, retained_target_label, successor.event, "observable"))
                loop_notes.append(f"{successor.event}->existing {retained_target_label}")
                continue

            raw_label = remember(targets, raw=True, tag=ObservationTag.UNKNOWN)
            known_edges.add((source_label, raw_label, successor.event, "observable"))

            next_label = remember(next_belief, raw=False, tag=ObservationTag.UNKNOWN)
            if next_belief != targets:
                known_edges.discard((source_label, raw_label, successor.event, "observable"))
                known_edges.add((source_label, next_label, successor.event, "observable"))
                known_nodes.discard(raw_label)
                raw_beliefs.discard(raw_label)
                layout_aliases.append((raw_label, next_label))

            add_ibts_transition(belief, successor.event, next_belief)
            loop_notes.append(f"{successor.event}->{next_label}")

            queued_beliefs = {item[0] for item in frontier}
            if next_belief not in visited and next_belief not in queued_beliefs:
                frontier.append((next_belief, next_trace))
                loop_notes.append(f"queued {next_label}")

        title = f"loop {loop_index}: expand {source_label}"
        pruning_preview = preview_pruning()
        if pruning_preview:
            loop_notes.append(describe_deleted(pruning_preview))
        if loop_notes:
            title += "; " + "; ".join(loop_notes)
        capture(title, source_label)
        apply_pruning()

    capture("fixed point: no belief frontier remains", None)
    return snapshots


def make_on_the_fly_snapshots(dfa: DFA) -> list[DeadlockSnapshot]:
    known_nodes: set[State] = {dfa.initial}
    known_edges: set[tuple[State, State, str]] = set()
    expanded: set[State] = set()
    frontier: deque[State] = deque([dfa.initial])
    previous_nondeadlock: set[State] = set()
    snapshots: list[DeadlockSnapshot] = []

    def capture(title: str) -> None:
        nonlocal previous_nondeadlock
        nondeadlock, deadlock = compute_deadlock_status(known_nodes, known_edges)
        restored = nondeadlock - previous_nondeadlock
        visible_frontier = set(frontier) | restored
        snapshots.append(
            DeadlockSnapshot(
                title=title,
                known_nodes=frozenset(known_nodes),
                known_edges=frozenset(known_edges),
                frontier=frozenset(visible_frontier),
                nondeadlock=frozenset(nondeadlock),
                deadlock=frozenset(deadlock),
            )
        )
        previous_nondeadlock = set(nondeadlock)

    capture("start from the initial state")
    while frontier:
        source = frontier.popleft()
        if source in expanded:
            continue
        expanded.add(source)

        for event, target in dfa.enabled(source):
            known_nodes.add(target)
            known_edges.add((source, target, event))
            if target not in expanded and target not in frontier:
                frontier.append(target)
            capture(f"discover {source} --{event}--> {target}")

    nondeadlock, deadlock = compute_deadlock_status(known_nodes, known_edges)
    title = "fixed point: no deadlock states remain"
    if deadlock:
        title = "fixed point: deadlock states remain"
    snapshots.append(
        DeadlockSnapshot(
            title=title,
            known_nodes=frozenset(known_nodes),
            known_edges=frozenset(known_edges),
            frontier=frozenset(),
            nondeadlock=frozenset(nondeadlock),
            deadlock=frozenset(deadlock),
        )
    )
    return snapshots


def _belief_label(belief: frozenset[State]) -> str:
    return "{" + ",".join(sorted(belief)) + "}"


def _tagged_belief_label(belief: frozenset[State], tag: ObservationTag) -> str:
    return tagged_belief_name(belief, tag)

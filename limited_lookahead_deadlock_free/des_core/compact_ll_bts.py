"""Bitset storage for the existing factored LL-BTS, with lazy public views.

Every D=(q,x) remains represented; all q in a successor estimate share the
same transitions. Construction visits x once, counts its |x| D nodes and
materializes their tuples only if a caller iterates the public view.
No plant/window/control semantics or cross-iteration cache is introduced.
"""

from array import array
from collections import deque
from collections.abc import Mapping, Set


def bits(mask):
    while mask:
        bit = mask & -mask
        mask ^= bit
        yield bit.bit_length() - 1


class DecisionView(Set):
    def __init__(self, graph):
        self.graph = graph

    def __len__(self):
        return self.graph.decision_count

    def __iter__(self):
        g = self.graph

        for mask in g.decisions:
            for member, _perm in g.orbit(mask):
                estimate = g.decode(member)

                for q in bits(member):
                    yield g.states[q], estimate

    def __contains__(self, item):
        root, estimate = item

        return root in estimate and self.graph.canonical(self.graph.encode(estimate))[0] in self.graph.d_ids


class ObservationView(Set):
    def __init__(self, graph):
        self.graph = graph

    def __len__(self):
        return self.graph.observation_count

    def __iter__(self):
        g = self.graph

        for oid in range(len(g.observations)):
            for mask, perm in g.orbit(g.observations[oid]):
                upper = g.upper[oid] if perm is None else g.symmetry.transform_pattern(g.upper[oid], perm)
                yield g.decode(mask), g.decode_pattern(upper)

    def __contains__(self, item):
        estimate, pattern = item
        g = self.graph
        mask, perm, _size = g.canonical(g.encode(estimate))
        oid = g.o_ids.get(mask, -1)

        if oid < 0:
            return False

        p = sum(1 << g.events.index(e) for e in pattern)

        if perm is not None:
            p = g.symmetry.transform_pattern(p, perm)

        return g.upper[oid] == p


class ChoiceView(Mapping):
    def __init__(self, graph):
        self.graph = graph

    def __len__(self):
        return sum(self.graph.canonical(mask)[2] for mask, choices in
                   zip(self.graph.decisions, self.graph.choices) if choices is not None)

    def __iter__(self):
        for did, mask in enumerate(self.graph.decisions):
            if self.graph.choices[did] is not None:
                for member, _perm in self.graph.orbit(mask):
                    yield self.graph.decode(member)

    def __getitem__(self, estimate):
        g = self.graph
        original = g.encode(estimate)
        canonical, _perm, _size = g.canonical(original)
        did = g.d_ids.get(canonical)

        if did is None or self.graph.choices[did] is None:
            raise KeyError(estimate)

        if g.symmetry is None:
            return tuple(g.decode_observation(oid) for oid in g.choices[did])

        choices = []

        for closure in g.closures(original):
            mask, perm, _size = g.canonical(closure)
            oid = g.o_ids.get(mask, -1)

            if oid >= 0:
                inverse = tuple(perm.index(i) for i in range(len(perm)))
                upper = g.symmetry.transform_pattern(g.upper[oid], inverse)
                choices.append((g.decode(closure), g.decode_pattern(upper)))

        return tuple(choices)


class CompactGraph:
    def __init__(self, plant, window, root, *, use_symmetry=True, maximal_hidden_only=False):
        self.maximal_hidden_only = maximal_hidden_only
        self.states = tuple(sorted(window))
        self.state_ids = {q: i for i, q in enumerate(self.states)}
        self.events = tuple(sorted(plant.events))
        event_ids = {e: i for i, e in enumerate(self.events)}
        self.control = sum(1 << event_ids[e] for e in plant.controllable)
        self.observable = sum(1 << event_ids[e] for e in plant.observable)
        self.uncontrollable = sum(1 << event_ids[e] for e in plant.uncontrollable)
        self.hidden_control = self.control & ~self.observable
        self.hidden_mandatory = self.uncontrollable & ~self.observable
        self.observable_control = self.control & self.observable
        self.observable_mandatory = self.uncontrollable & self.observable
        self.hidden_edges = []
        self.enabled = []
        self.sources = [0] * len(self.events)
        self.transitions = [{} for _ in self.events]
        self.deadlocks = 0
        self.interior = 0

        for qi, q in enumerate(self.states):
            enabled = 0
            hidden = []

            for event, target in plant.enabled(q):
                ei = event_ids[event]
                eb = 1 << ei
                enabled |= eb
                self.sources[ei] |= 1 << qi
                ti = self.state_ids.get(target)

                if ti is not None:
                    tb = 1 << ti
                    self.interior |= 1 << qi
                    self.transitions[ei][1 << qi] = tb

                    if not eb & self.observable:
                        hidden.append((eb, tb))

            self.enabled.append(enabled)
            self.hidden_edges.append(tuple(hidden))

            if not enabled:
                self.deadlocks |= 1 << qi

        self.decisions = []
        self.d_ids = {}
        self.choices = []
        self.incoming_outcomes = []
        self.observations = []
        self.o_ids = {}  # -1 denotes a locally inconsistent family.
        self.upper = []
        self.targets = []
        self.requirements = []
        self.incoming_controls = []
        self.decision_count = 0
        self.edge_count = 0
        self.decision_union = 0
        self.observation_union = 0
        self.observation_count = 0
        from des_core.product_symmetry import make_symmetry

        self.symmetry = make_symmetry(self, plant, root) if use_symmetry else None

    def canonical(self, mask):
        if self.symmetry is None or mask < 0:
            return mask, None, 1

        return self.symmetry.canonical(mask)

    def orbit(self, mask):
        if self.symmetry is None:
            yield mask, None
        else:
            yield from self.symmetry.orbit(mask)

    def orbit_union(self, mask):
        return mask if self.symmetry is None else self.symmetry.union(mask)

    def encode(self, estimate):
        mask = 0

        for q in estimate:
            qi = self.state_ids.get(q)

            if qi is None:
                return -1

            mask |= 1 << qi

        return mask

    def decode(self, mask):
        return frozenset(self.states[i] for i in bits(mask))

    def decode_pattern(self, mask):
        return frozenset(self.events[i] for i in bits(mask))

    def decode_observation(self, oid):
        return self.decode(self.observations[oid]), self.decode_pattern(self.upper[oid])

    def add_decision(self, mask):
        mask, _perm, size = self.canonical(mask)
        did = self.d_ids.get(mask)

        if did is not None:
            return did

        did = len(self.decisions)
        self.d_ids[mask] = did
        self.decisions.append(mask)
        self.choices.append(None)
        self.incoming_outcomes.append(array('I'))
        self.decision_union |= self.orbit_union(mask)
        self.decision_count += mask.bit_count() * size

        return did

    def post(self, mask, ei):
        reached = 0
        remaining = mask & self.sources[ei]
        transitions = self.transitions[ei]

        while remaining:
            bit = remaining & -remaining
            remaining ^= bit
            reached |= transitions.get(bit, 0)

        return reached

    def close(self, reached, enabled, frontier):
        """Incrementally close newly reached states under a fixed hidden choice."""

        enabled |= self.hidden_mandatory

        while frontier:
            bit = frontier & -frontier
            frontier ^= bit

            for event, target in self.hidden_edges[bit.bit_length() - 1]:
                if event & enabled and not target & reached:
                    reached |= target
                    frontier |= target

        return reached

    def closures(self, seeds):
        if self.maximal_hidden_only:
            reached = self.close(seeds, self.hidden_control, seeds)

            if not reached & self.deadlocks:
                yield reached

            return

        reached = self.close(seeds, 0, seeds)
        stack = [(reached, 0, 0)]
        seen = set()

        while stack:
            reached, enabled, disabled = stack.pop()

            if reached & self.deadlocks:
                continue

            unknown = 0

            for qi in bits(reached):
                for event, target in self.hidden_edges[qi]:
                    if not target & reached:
                        unknown |= event

            unknown &= self.hidden_control & ~(enabled | disabled)

            if unknown:
                event = unknown & -unknown
                stack.append((reached, enabled, disabled | event))
                added = self.post(reached, event.bit_length() - 1) & ~reached
                expanded = self.close(reached | added, enabled | event, added)
                stack.append((expanded, enabled | event, disabled))
            elif reached not in seen:
                seen.add(reached)
                yield reached

    def observation(self, mask):
        mask, _perm, size = self.canonical(mask)
        oid = self.o_ids.get(mask)

        if oid is not None:
            return oid

        forbidden = 0
        occurs = 0

        for qi in bits(mask):
            occurs |= self.enabled[qi] & self.observable

            for event, target in self.hidden_edges[qi]:
                if not target & mask:
                    forbidden |= event

        upper = self.control & ~forbidden
        successors = []

        for ei in bits(occurs):
            target = self.post(mask, ei)

            if target:
                successors.append((ei, target))

            # An observable transition that leaves x_L is a horizon boundary,
            # not an O-state inconsistency: it has no local NX successor.
        fixed = (upper & ~self.observable) | self.uncontrollable
        enabled_obs = upper & self.observable
        oid = len(self.observations)
        self.o_ids[mask] = oid
        self.observations.append(mask)
        self.observation_count += size
        self.upper.append(upper)
        self.requirements.append(())
        self.incoming_controls.append(array('I'))
        self.observation_union |= self.orbit_union(mask)
        targets = array('I')

        for ei, target in successors:
            did = self.add_decision(target)
            targets.extend((ei, did))
            self.incoming_outcomes[did].extend((oid, ei))
            self.edge_count += target.bit_count() * size

        self.targets.append(targets)

        return oid

    def construct(self, root, progress):
        self.add_decision(1 << self.state_ids[root])
        did = 0

        while did < len(self.decisions):
            seeds = self.decisions[did]

            if not seeds & self.deadlocks:
                choices = array('I')

                for closure in self.closures(seeds):
                    oid = self.observation(closure)

                    if oid >= 0:
                        choices.append(oid)
                        self.incoming_controls[oid].append(did)

                self.choices[did] = choices
                self.edge_count += seeds.bit_count() * len(choices) * self.canonical(seeds)[2]

            did += 1

            if progress is not None and did % 256 == 0:
                progress(self.decision_count, self.observation_count, len(self.decisions) - did)

        if progress is not None:
            progress(self.decision_count, self.observation_count, 0)

    def synthesize(self):
        from des_core.ll_bts import _maximal_patterns
        from des_core.ll_bts_synthesis import LLBTSControlResult

        losing_d = bytearray(len(self.decisions))
        losing_o = bytearray(len(self.observations))
        remaining = [len(c) if c is not None else 0 for c in self.choices]
        allowed = [upper & self.observable_control for upper in self.upper]
        queue = deque()

        for did, mask in enumerate(self.decisions):
            if mask & self.deadlocks or not remaining[did]:
                losing_d[did] = 1
                queue.append(did)

        while queue:
            node = queue.popleft()

            if node < 0:
                oid = -node - 1

                for did in self.incoming_controls[oid]:
                    if not losing_d[did]:
                        remaining[did] -= 1

                        if not remaining[did]:
                            losing_d[did] = 1
                            queue.append(did)

                continue

            outcomes = self.incoming_outcomes[node]

            for pos in range(0, len(outcomes), 2):
                oid, ei = outcomes[pos], outcomes[pos + 1]

                if losing_o[oid]:
                    continue

                event = 1 << ei

                if event & self.observable_mandatory:
                    invalid = True
                else:
                    allowed[oid] &= ~event
                    invalid = any(not req & allowed[oid] for req in self.requirements[oid])

                if invalid:
                    losing_o[oid] = 1
                    queue.append(-oid - 1)

        if losing_d[0]:
            return LLBTSControlResult(True, (), ())

        patterns = {}

        for oid in set(self.choices[0]):
            if not losing_o[oid]:
                pattern = (self.upper[oid] & ~self.observable) | allowed[oid]
                members = ((pattern, None),) if self.symmetry is None else self.symmetry.orbit(pattern, pattern=True)

                for member, perm in members:
                    patterns[self.decode_pattern(member)] = (oid, perm)

        maximal = _maximal_patterns(patterns)
        maximal_set = set(maximal)
        forward = set()

        for pattern, (oid, perm) in patterns.items():
            if pattern not in maximal_set:
                continue

            targets = self.targets[oid]
            enabled = allowed[oid] | self.observable_mandatory

            for pos in range(0, len(targets), 2):
                ei, did = targets[pos], targets[pos + 1]

                if (1 << ei) & enabled:
                    event = self.events[ei]

                    if perm is not None:
                        event = self.events[self.symmetry.transform_pattern(1 << ei, perm).bit_length() - 1]

                    for qi in bits(self.post(self.observations[oid], ei)):
                        root = self.states[qi]

                        if perm is not None:
                            root = self.symmetry.transform_state(root, perm)

                        forward.add((pattern, event, root))

        return LLBTSControlResult(False, maximal, tuple(sorted(
            forward, key=lambda item: (len(item[0]), sorted(item[0]), item[1], item[2])
        )))


def construct_compact(plant, current, window, progress, *, use_symmetry=True,
                      maximal_hidden_only=False):
    from des_core.ll_bts import LLBTSResult, _maximal_patterns

    graph = CompactGraph(plant, window, current, use_symmetry=use_symmetry,
                         maximal_hidden_only=maximal_hidden_only)
    graph.construct(current, progress)
    good = set()

    for oid in set(graph.choices[0] or ()):
        if not graph.observations[oid] & ~graph.interior:
            upper = graph.upper[oid]
            members = ((upper, None),) if graph.symmetry is None else graph.symmetry.orbit(upper, pattern=True)
            good.update(graph.decode_pattern(mask) for mask, _perm in members)

    d_union = graph.decode(graph.decision_union)
    o_union = graph.decode(graph.observation_union)

    return LLBTSResult(
        DecisionView(graph), ObservationView(graph), ChoiceView(graph), frozenset(),
        graph.edge_count, window, d_union, o_union, d_union | o_union,
        _maximal_patterns(good), 'factored', graph,
    )

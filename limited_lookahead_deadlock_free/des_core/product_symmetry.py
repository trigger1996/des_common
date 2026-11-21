"""Exact coordinate permutations fixing a repeated product's current root.

Only equal components at the same root coordinate may be exchanged. The
window, event partitions, UR/NX and consistency are invariant under this group.
Canonicalization uses column histograms then exhausts unresolved permutations;
histograms alone are never taken as an equivalence test.
"""

from collections import defaultdict, deque
from itertools import permutations, product
from math import factorial, prod


class ProductSymmetry:
    def __init__(self, graph, plant, root):
        self.states = graph.states
        self.state_ids = graph.state_ids
        self.events = graph.events
        self.n = len(root)
        groups = defaultdict(list)

        for i, q in enumerate(root):
            groups[q].append(i)

        self.groups = tuple(tuple(g) for g in groups.values())
        self.order = prod(factorial(len(g)) for g in self.groups)
        self.identity = tuple(range(self.n))
        self.local_states = tuple(sorted(plant.components[0].states))
        self.local_ids = {q: i for i, q in enumerate(self.local_states)}
        event_ids = {e: i for i, e in enumerate(graph.events)}
        self.event_coordinates = {}

        for i in range(self.n):
            for e in plant.components[0].events:
                self.event_coordinates[event_ids[f'{e}_{i}']] = (e, i)

        self.event_ids = event_ids
        self.state_maps = {}
        self.event_maps = {}
        self.cache = {}
        self.orbit_sizes = {}
        self.generators = []

        for group in self.groups:
            for i, j in zip(group, group[1:]):
                p = list(self.identity)
                p[i], p[j] = j, i
                self.generators.append(tuple(p))

        state_orbits = defaultdict(int)
        keys = []

        for qi, q in enumerate(graph.states):
            key = tuple(tuple(sorted(q[i] for i in group)) for group in self.groups)
            keys.append(key)
            state_orbits[key] |= 1 << qi

        self.state_orbits = [state_orbits[k] for k in keys]

    def transform_state(self, q, perm):
        out = [None] * self.n

        for old, new in enumerate(perm):
            out[new] = q[old]

        return tuple(out)

    def transform(self, mask, perm):
        if perm == self.identity:
            return mask

        table = self.state_maps.get(perm)

        if table is None:
            table = tuple(1 << self.state_ids[self.transform_state(q, perm)]
                          for q in self.states)
            self.state_maps[perm] = table

        out = 0

        while mask:
            bit = mask & -mask
            mask ^= bit
            out |= table[bit.bit_length() - 1]

        return out

    def transform_pattern(self, mask, perm):
        if perm == self.identity:
            return mask

        table = self.event_maps.get(perm)

        if table is None:
            table = tuple(1 << self.event_ids[f'{e}_{perm[i]}']
                          for ei in range(len(self.events))
                          for e, i in (self.event_coordinates[ei],))
            self.event_maps[perm] = table

        out = 0

        while mask:
            bit = mask & -mask
            mask ^= bit
            out |= table[bit.bit_length() - 1]

        return out

    def canonical(self, mask):
        cached = self.cache.get(mask)

        if cached is not None:
            return cached

        hist = [[0] * len(self.local_states) for _ in range(self.n)]
        remaining = mask

        while remaining:
            bit = remaining & -remaining
            remaining ^= bit
            q = self.states[bit.bit_length() - 1]

            for i, state in enumerate(q):
                hist[i][self.local_ids[state]] += 1

        first = list(self.identity)
        ties = []

        for group in self.groups:
            ordered = sorted(group, key=lambda i: hist[i])
            same = defaultdict(list)

            for old, new in zip(ordered, group):
                first[old] = new
                same[tuple(hist[old])].append(new)

            ties.extend(tuple(v) for v in same.values() if len(v) > 1)

        first = tuple(first)
        base = self.transform(mask, first)
        unresolved = []
        stabilizer_factor = 1

        for tie in ties:
            invariant = True

            for i, j in zip(tie, tie[1:]):
                swap = list(self.identity)
                swap[i], swap[j] = j, i

                if self.transform(base, tuple(swap)) != base:
                    invariant = False

                    break

            if invariant:
                stabilizer_factor *= factorial(len(tie))
            else:
                unresolved.append(tie)

        best = None
        best_perm = None
        multiplicity = 0

        for choices in product(*(permutations(tie) for tie in unresolved)):
            second = list(self.identity)

            for tie, destinations in zip(unresolved, choices):
                for old, new in zip(tie, destinations):
                    second[old] = new

            candidate = self.transform(base, tuple(second))

            if best is None or candidate < best:
                best = candidate
                best_perm = tuple(second[first[i]] for i in range(self.n))
                multiplicity = 1
            elif candidate == best:
                multiplicity += 1

        size = self.order // (stabilizer_factor * multiplicity)
        result = best, best_perm, size
        self.cache[mask] = result
        self.cache.setdefault(best, (best, self.identity, size))
        self.orbit_sizes[best] = size

        return result

    def union(self, mask):
        union = 0

        while mask:
            bit = mask & -mask
            mask ^= bit
            union |= self.state_orbits[bit.bit_length() - 1]

        return union

    def orbit(self, mask, *, pattern=False):
        transform = self.transform_pattern if pattern else self.transform
        seen = {mask}
        queue = deque([(mask, self.identity)])

        while queue:
            current, perm = queue.popleft()
            yield current, perm

            for generator in self.generators:
                other = transform(current, generator)

                if other not in seen:
                    seen.add(other)
                    queue.append((other, tuple(generator[perm[i]] for i in range(self.n))))


def make_symmetry(graph, plant, root):
    components = getattr(plant, 'components', ())

    if len(components) < 2 or any(c != components[0] for c in components[1:]):
        return None

    symmetry = ProductSymmetry(graph, plant, root)

    return symmetry if symmetry.order > 1 else None

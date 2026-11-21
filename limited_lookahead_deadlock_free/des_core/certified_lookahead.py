"""Draft's offline certificates followed by sound, estimate-based online synthesis.

Unlike the legacy optimistic LL-BTS, an uncertified horizon boundary never proves
safety. Patterns store only controllable events; all uncontrollable events are
implicitly enabled. Online state is the complete observation estimate, not a
measured physical state. No cross-query synthesis cache is used.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace
from itertools import combinations
from time import perf_counter

from des_core.automata import DFA

Estimate = frozenset[str]
Pattern = frozenset[str]


@dataclass(frozen=True)
class Preprocessing:
    plant: DFA
    deadlocks: Estimate
    failure: Estimate
    safe: Estimate
    entries: Estimate
    horizon: int
    risk_horizon: int
    path_visits: int
    seconds: float


def preprocess(plant: DFA, *, max_path_visits: int | None = None) -> Preprocessing:
    """Algorithm 1, final version: targets Q_f union Q_e; initial entry included.

    Distinct successors and unobservable predecessors are state sets, not event
    counts. Iterative DFS backtracks path marks and computes the exact longest
    simple path, even in cyclic hidden graphs. An explicit budget raises rather
    than silently returning an underestimated u. Q_d is excluded from Q_f.
    """
    started = perf_counter()
    if plant.initial not in plant.states:
        raise ValueError("initial state outside Q")
    if not plant.controllable <= plant.events or not plant.observable <= plant.events:
        raise ValueError("event partition outside Sigma")
    successors = {q: set() for q in plant.states}
    predecessors = {q: set() for q in plant.states}
    hidden_predecessors = {q: set() for q in plant.states}
    candidates = {plant.initial}
    for (q, event), target in plant.transitions.items():
        if q not in plant.states or target not in plant.states or event not in plant.events:
            raise ValueError("transition outside declared DFA")
        successors[q].add(target)
        predecessors[target].add(q)
        if event in plant.observable:
            candidates.add(target)
        else:
            hidden_predecessors[target].add(q)
    deadlocks = frozenset(q for q in plant.states if not successors[q])
    removed, failure = set(deadlocks), set()
    queue = deque(sorted(deadlocks))
    while queue:
        target = queue.popleft()
        for q in sorted(predecessors[target]):
            if q in removed:
                continue
            if successors[q] == {target} and target in deadlocks | failure:
                failure.add(q)
            removed.add(q)
            queue.append(q)
    safe = plant.states - removed
    entries, horizon, risk_horizon, visits = set(), 0, 0, 0
    hidden_predecessors = {q: tuple(sorted(v)) for q, v in hidden_predecessors.items()}
    for target in sorted(failure | safe):
        path = {target}
        stack = [(target, iter(hidden_predecessors[target]))]
        while stack:
            q, iterator = stack[-1]
            # Count and inspect each path once, on entry, not on backtracking.
            if iterator is None:
                raise AssertionError("invalid DFS frame")
            nxt = next(iterator, None)
            if nxt is None:
                path.remove(q)
                stack.pop()
                continue
            if nxt in path:
                continue
            path.add(nxt)
            visits += 1
            if max_path_visits is not None and visits > max_path_visits:
                raise RuntimeError("exact longest-simple-path preprocessing budget exceeded")
            depth = len(path) - 1
            if nxt in candidates:
                entries.add(nxt)
                horizon = max(horizon, depth)
                if target in failure:
                    risk_horizon = max(risk_horizon, depth)
            stack.append((nxt, iter(hidden_predecessors[nxt])))
        # A zero-length entry path contributes to Q_o, including u=0 cases.
        visits += 1
        if max_path_visits is not None and visits > max_path_visits:
            raise RuntimeError("exact longest-simple-path preprocessing budget exceeded")
        if target in candidates:
            entries.add(target)
    return Preprocessing(plant, deadlocks, frozenset(failure), frozenset(safe),
                         frozenset(entries), horizon, risk_horizon, visits,
                         perf_counter() - started)


@dataclass(frozen=True)
class Choice:
    pattern: Pattern
    closure: Estimate
    successors: tuple[tuple[str, Estimate], ...]


@dataclass
class CertifiedResult:
    status: str  # winning, losing (proved), or inconclusive (window insufficient)
    initial: Estimate
    horizon: int | None
    window: Estimate
    policy: dict[Estimate, tuple[Choice, ...]]
    safe_terminals: frozenset[Estimate]
    decision_count: int
    observation_count: int
    edge_count: int
    boundary_choices: int
    seconds: float
    all_controllable: Pattern
    constructed_choices: dict[Estimate, tuple[Choice, ...]]

    @property
    def maximal_patterns(self) -> tuple[Pattern, ...]:
        if self.initial in self.safe_terminals:
            return (self.all_controllable,)
        patterns = {c.pattern for c in self.policy.get(self.initial, ())}
        return tuple(sorted((p for p in patterns if not any(p < q for q in patterns)),
                            key=lambda p: (len(p), sorted(p))))


def _patterns(plant):
    events = sorted(plant.controllable)
    return (frozenset(c) for n in range(len(events) + 1)
            for c in combinations(events, n))


def complete_choice(plant: DFA, estimate: Estimate, pattern: Pattern) -> Choice:
    """Complete UR and NX; never intersect an estimate with the window."""
    enabled = pattern | plant.uncontrollable
    reached, queue = set(estimate), deque(sorted(estimate))
    while queue:
        q = queue.popleft()
        for event, target in plant.enabled(q):
            if event in enabled and event not in plant.observable and target not in reached:
                reached.add(target)
                queue.append(target)
    targets = defaultdict(set)
    for q in sorted(reached):
        for event, target in plant.enabled(q):
            if event in enabled and event in plant.observable:
                targets[event].add(target)
    return Choice(pattern, frozenset(reached),
                  tuple((e, frozenset(v)) for e, v in sorted(targets.items())))


def solve_certified(pre: Preprocessing, estimate: Estimate | None = None,
                    horizon: int | None = None, *, full: bool = False,
                    certificates: bool = True, max_choices: int | None = None,
                    max_window_states: int | None = None,
                    timeout_seconds: float | None = None) -> CertifiedResult:
    """Construct merged-estimate BTS and count-prune its greatest fixed point.

    A full solve (window=Q) is an exact offline deadlock-free baseline. With a
    finite window, complete UR/NX are checked; out-of-window choices without a
    Q_e certificate are unavailable, but recorded for an optimistic second pass.
    Only if that second pass also loses do we report proved losing. Otherwise
    failure to find a sound controller is inconclusive, never 'no supervisor'.
    A pre-certified safe initial estimate stops before window enumeration;
    in that case result.window contains only materialized initial states.
    """
    started = perf_counter()
    tested=0
    def check_budget(window_count):
        reason=('choice budget exceeded' if max_choices is not None and tested>=max_choices else
                'window budget exceeded' if max_window_states is not None and window_count>max_window_states else
                'time budget exceeded' if timeout_seconds is not None and perf_counter()-started>=timeout_seconds else None)
        if reason:
            from des_core.offline_bts import BTSBudgetExceeded
            raise BTSBudgetExceeded(reason,seconds=perf_counter()-started,
                patterns_tested=tested,window_states=window_count,complete=False)
    plant = pre.plant
    initial = frozenset({plant.initial}) if estimate is None else frozenset(estimate)
    if not initial or not initial <= plant.states:
        raise ValueError("estimate must be a nonempty subset of Q")
    horizon = pre.horizon if horizon is None else horizon
    if horizon < 0:
        raise ValueError("horizon must be nonnegative")
    # A proved forward-invariant all-live Qe needs no local window expansion.
    # Check BEFORE constructing Post_<=u: on a large known product that scan can
    # otherwise dominate work despite the already-complete safety certificate.
    if certificates and not full and initial <= pre.safe:
        return CertifiedResult('winning',initial,horizon,initial,{initial:()},
            frozenset((initial,)),1,0,0,0,perf_counter()-started,
            plant.controllable,{initial:()})
    window = set(plant.states) if full else set(initial)
    frontier = set(initial)
    if not full:
        for _ in range(horizon):
            targets = {t for q in frontier for _, t in plant.enabled(q)} - window
            window.update(targets)
            check_budget(len(window))
            frontier = targets
            if not frontier:
                break
    window = frozenset(window)
    bad_states = pre.deadlocks | (pre.failure if certificates else frozenset())
    safe = pre.safe if certificates else frozenset()
    choices, terminals, boundaries = {}, set(), defaultdict(int)
    queue, seen = deque([initial]), {initial}
    while queue:
        x = queue.popleft()
        choices[x] = []
        if x & bad_states:
            continue
        if x <= safe:
            terminals.add(x)
            continue  # implicit gamma=Sigma, no UR/NX or O node expansion
        for pattern in _patterns(plant):
            check_budget(len(window))
            choice = complete_choice(plant, x, pattern)
            tested+=1
            enabled = pattern | plant.uncontrollable
            if choice.closure & bad_states or any(
                not any(e in enabled for e, _ in plant.enabled(q)) for q in choice.closure
            ):
                continue
            if not choice.closure <= window or any(
                not y <= window and not y <= safe for _, y in choice.successors
            ):
                boundaries[x] += 1
                continue
            choices[x].append(choice)
            for _, y in choice.successors:
                if y not in seen:
                    seen.add(y)
                    queue.append(y)

    def prune(optimistic=False):
        remaining = {x: len(v) + (boundaries[x] if optimistic else 0)
                     for x, v in choices.items()}
        incoming = defaultdict(list)
        for x, options in choices.items():
            for i, choice in enumerate(options):
                for y in {y for _, y in choice.successors}:
                    incoming[y].append((x, i))
        lost = {x for x, count in remaining.items() if not count and x not in terminals}
        work, removed = deque(sorted(lost, key=lambda x: sorted(x))), set()
        while work:
            y = work.popleft()
            for x, i in incoming[y]:
                if (x, i) in removed:
                    continue
                removed.add((x, i))
                remaining[x] -= 1
                if not remaining[x] and x not in lost and x not in terminals:
                    lost.add(x)
                    work.append(x)
        return lost, removed

    lost, removed = prune()
    policy = {x: tuple(c for i, c in enumerate(v) if (x, i) not in removed)
              for x, v in choices.items() if x not in lost}
    # Safe terminals have a compact implicit all-events policy. The helper below
    # computes complete observable updates only when execution needs them.
    status = 'winning' if initial not in lost else (
        'inconclusive' if initial not in prune(True)[0] else 'losing')
    observation_nodes = {(c.closure, c.pattern) for v in choices.values() for c in v}
    edges = {(x, c.closure, c.pattern) for x, v in choices.items() for c in v}
    obs_edges = {(c.closure, c.pattern, e, y)
                 for v in choices.values() for c in v for e, y in c.successors}
    result = CertifiedResult(status, initial, None if full else horizon, window, policy,
                             frozenset(terminals), len(choices), len(observation_nodes),
                             len(edges) + len(obs_edges), sum(boundaries.values()),
                             perf_counter() - started, plant.controllable,
                             {x: tuple(v) for x, v in choices.items()})
    return result


def executable_choices(pre: Preprocessing, result: CertifiedResult,
                       estimate: Estimate) -> tuple[Choice, ...]:
    if estimate in result.safe_terminals:
        return (complete_choice(pre.plant, estimate, pre.plant.controllable),)
    return result.policy.get(estimate, ())


def solve_offline(plant: DFA, estimate: Estimate | None = None) -> CertifiedResult:
    """Full BTS baseline for the SAME deadlock-free objective and pruning code.

    Independently constructs the complete known-system UR/NX BTS, including
    unsafe branches, before count pruning. No Q_f/Q_e, horizon, or longest
    simple paths. Not a reproduction of Yin's other property specifications
    or the original quadratic pruning implementation.
    """
    from des_core.offline_bts import construct_offline_bts
    return construct_offline_bts(plant,estimate)


class CertifiedController:
    """Re-solve with complete beliefs; retain a proved continuation as fallback.

    Receding fixed windows need not retain the previous proof's whole graph.
    A fresh inconclusive solve must not discard an already certified policy.
    The stored proof is query-local controller memory, not a synthesis cache.
    """
    def __init__(self, pre: Preprocessing, horizon: int | None = None):
        self.pre = pre
        self.horizon = pre.horizon if horizon is None else horizon
        self.estimate = frozenset({pre.plant.initial})
        self.proof = None

    def solve(self):
        fresh = solve_certified(self.pre, self.estimate, self.horizon)
        fallback = False
        if fresh.status == 'winning':
            self.proof = fresh
        elif self.proof is not None and executable_choices(self.pre, self.proof, self.estimate):
            self.proof = replace(self.proof, initial=self.estimate)
            fallback = True
        else:
            return fresh, fresh, False
        return self.proof, fresh, fallback

    def observe(self, pattern: Pattern, event: str):
        if self.proof is None:
            raise ValueError('solve before executing a control')
        options = executable_choices(self.pre, self.proof, self.estimate)
        choice = next((c for c in options if c.pattern == pattern), None)
        if choice is None:
            raise ValueError('pattern not certified at current estimate')
        successor = dict(choice.successors).get(event)
        if successor is None:
            raise ValueError('observation impossible under selected pattern')
        self.estimate = successor
        return successor


def validate_policy(pre: Preprocessing, result: CertifiedResult) -> dict[str, int]:
    """Exhaustively verify every reachable state/observation of every policy choice."""
    if result.status != 'winning':
        return {'estimates': 0, 'choices': 0}
    queue, seen, count = deque([result.initial]), set(), 0
    while queue:
        x = queue.popleft()
        if x in seen:
            continue
        seen.add(x)
        if x <= pre.safe and x in result.safe_terminals:
            assert all(pre.plant.enabled(q) and all(t in pre.safe for _, t in pre.plant.enabled(q))
                       for q in x)
            continue
        options = executable_choices(pre, result, x)
        assert options, ('missing control', x)
        for choice in options:
            count += 1
            actual = complete_choice(pre.plant, x, choice.pattern)
            assert actual == choice, ('incomplete estimate', x)
            assert not actual.closure & pre.deadlocks
            enabled = choice.pattern | pre.plant.uncontrollable
            assert all(any(e in enabled for e, _ in pre.plant.enabled(q)) for q in actual.closure)
            for _, y in actual.successors:
                assert y in result.policy or y in result.safe_terminals, ('missing outcome', y)
                queue.append(y)
    return {'estimates': len(seen), 'choices': count}

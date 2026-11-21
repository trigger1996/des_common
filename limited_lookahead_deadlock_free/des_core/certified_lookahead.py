"""Draft's offline certificates followed by sound, estimate-based online synthesis.

Unlike the legacy optimistic LL-BTS, an uncertified horizon boundary never proves
safety. Patterns store only controllable events; all uncontrollable events are
implicitly enabled. Online state is the complete observation estimate, not a
measured physical state. No cross-query synthesis cache is used.

Paper notation used below:
    Q_d / Q_f / Q_e: plant deadlocks / failure-chain states / all-future-safe states.
    Q_o_tilde: observable-entry set with targets extended to Q_f union Q_e.
    u: lookahead_lower_bound computed by preprocessing; x_L: lookahead window.
    x_hat: decision estimate; x: UR closure at an observation node.
    gamma_c: selected controllable events; gamma = gamma_c union Sigma_uc.
Public estimate/pattern/horizon arguments retain their existing API names.
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
    Q_d: Estimate
    Q_f: Estimate
    Q_e: Estimate
    Q_o_tilde: Estimate
    u: int  # lookahead_lower_bound for targets Q_f union Q_e; reported as draft_u.
    u_f: int  # Diagnostic bound restricted to targets in Q_f.
    path_visits: int
    seconds: float

    # Compatibility names used by existing benchmarks, exports and controllers.
    @property
    def deadlocks(self) -> Estimate:
        return self.Q_d

    @property
    def failure(self) -> Estimate:
        return self.Q_f

    @property
    def safe(self) -> Estimate:
        return self.Q_e

    @property
    def entries(self) -> Estimate:
        return self.Q_o_tilde

    @property
    def horizon(self) -> int:
        return self.u

    @property
    def risk_horizon(self) -> int:
        return self.u_f


def preprocess(plant: DFA, *, max_path_visits: int | None=None) -> Preprocessing:
    """Algorithm 1, final version: targets Q_f union Q_e; initial entry included.

    Entry point for computing lookahead_lower_bound: compute Q_d/Q_f/Q_e and
    the draft lookahead threshold u, returned as pre.u (also accessible through
    the compatibility name pre.horizon, reported as draft_u).
    This function does not search for the minimum decisive u or
    the minimum u that recovers the offline maximal root control patterns;
    benchmark scripts find those values by repeatedly calling solve_limited_lookahead.
    The threshold itself does not replace policy safety certification.

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

    # ### 1. 建立状态之间的关系
    # Cache Post(q), Pre(q), and Pre_uo(q) as distinct STATE sets.
    # Multiple event labels with the same endpoints count as one successor.
    # Q_entry contains q_0 and every observable-event target, before filtering.
    Post = {q: set() for q in plant.states}
    Pre = {q: set() for q in plant.states}
    Pre_uo = {q: set() for q in plant.states}
    Q_entry = {plant.initial}

    for (q, sigma), q_v in plant.transitions.items():
        if q not in plant.states or q_v not in plant.states or sigma not in plant.events:
            raise ValueError("transition outside declared DFA")

        Post[q].add(q_v)
        Pre[q_v].add(q)

        if sigma in plant.observable:
            Q_entry.add(q_v)
        else:
            Pre_uo[q_v].add(q)

    # ### 2. 找出死锁集合 Q_d
    # Q_d contains exactly the states with no plant transition.
    Q_d = frozenset(q for q in plant.states if not Post[q])
    # ### 3. 从 Q_d 反向搜索，计算 Q_f 和 Q_e
    Q_reach_d, Q_f = set(Q_d), set()
    W = deque(sorted(Q_d))

    # W is the paper's backward FIFO work queue.
    # Q_reach_d accumulates all states that can reach Q_d along ANY event path.
    # A predecessor belongs to Q_f only when its sole successor STATE is in
    # Q_d union Q_f; Q_f is not the complete set of losing information states.
    while W:
        q_v = W.popleft()

        for q in sorted(Pre[q_v]):
            if q in Q_reach_d:
                continue

            if Post[q] == {q_v} and q_v in Q_d | Q_f:
                Q_f.add(q)

            Q_reach_d.add(q)
            W.append(q)

    # Q_e is the complement of Pre*(Q_d). Every transition from Q_e stays in Q_e,
    # so enabling all events gives a deadlock-free continuation there.
    Q_e = plant.states - Q_reach_d
    Q_o_tilde, u, u_f, path_visits = set(), 0, 0, 0
    Pre_uo = {q: tuple(sorted(v)) for q, v in Pre_uo.items()}

    # ### 4. 计算 lookahead_lower_bound，也就是 u
    # Enumerate backward unobservable SIMPLE
    # paths from each q_v in Q_f union Q_e. P is the current-path state set;
    # ell counts transitions. Reaching Q_entry updates Q_o_tilde and u.
    # This implements the draft's extended target set, not only Q_f.
    # u_f separately records the bound with Q_f targets only.
    for q_v in sorted(Q_f | Q_e):
        P = {q_v}
        dfs_stack = [(q_v, iter(Pre_uo[q_v]))]

        while dfs_stack:
            q, pred_iter = dfs_stack[-1]

            # Count and inspect each path once, on entry, not on backtracking.
            if pred_iter is None:
                raise AssertionError("invalid DFS frame")

            q_s = next(pred_iter, None)

            if q_s is None:
                # Backtrack: release path membership so another simple path
                # may visit q again. A global visited set would miss long paths.
                P.remove(q)
                dfs_stack.pop()

                continue

            if q_s in P:
                # Skip a repeated state only on the CURRENT path, avoiding
                # infinite traversal of an unobservable cycle.
                continue

            P.add(q_s)
            path_visits += 1

            if max_path_visits is not None and path_visits > max_path_visits:
                raise RuntimeError("exact longest-simple-path preprocessing budget exceeded")

            ell = len(P) - 1

            if q_s in Q_entry:
                Q_o_tilde.add(q_s)
                # u = max length among the eligible entry-to-target paths.
                u = max(u, ell)

                if q_v in Q_f:
                    u_f = max(u_f, ell)

            dfs_stack.append((q_s, iter(Pre_uo[q_s])))

        # A zero-length entry path contributes to Q_o_tilde, including u=0.
        path_visits += 1

        if max_path_visits is not None and path_visits > max_path_visits:
            raise RuntimeError("exact longest-simple-path preprocessing budget exceeded")

        if q_v in Q_entry:
            Q_o_tilde.add(q_v)

    # ### 5. 将分析结果交给综合器
    # Return certificates and u; solve_limited_lookahead still checks policy safety.
    return Preprocessing(plant, Q_d, frozenset(Q_f), frozenset(Q_e),
                         frozenset(Q_o_tilde), u, u_f, path_visits,
                         perf_counter() - started)


@dataclass(frozen=True)
class Choice:
    pattern: Pattern  # gamma_c = gamma intersect Sigma_c; Sigma_uc is implicit.
    closure: Estimate  # x = UR_gamma(x_hat), intersected with x_L for local choices.
    successors: tuple[tuple[str, Estimate], ...]  # NX_sigma_o(x), clipped for local choices.


@dataclass
class Bipartitle_System:
    """BTS/LL-BTS construction, retained policy, and synthesis outcome.

    Shared by online LL-BTS and traditional offline BTS. This container is
    not yet a selected supervisor or its reachable closed-loop product.
    """

    status: str  # winning, losing (proved), or inconclusive (window insufficient)
    initial: Estimate  # Initial decision estimate x_hat_0.
    horizon: int | None  # Chosen u; None for a full offline construction.
    window: Estimate  # x_L = Post_{<=u}(x_hat_0), subject to certificate shortcut.
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


def _unobservable_reach(plant: DFA, estimate: Estimate, pattern: Pattern) -> Estimate:
    """Zero or more enabled hidden transitions, with no endpoint restriction."""

    gamma = pattern | plant.uncontrollable
    x, queue = set(estimate), deque(sorted(estimate))

    while queue:
        q = queue.popleft()

        for sigma, q_next in plant.enabled(q):
            if sigma in gamma and sigma not in plant.observable and q_next not in x:
                x.add(q_next)
                queue.append(q_next)

    return frozenset(x)


def limited_ur(plant: DFA, x_hat: Estimate, gamma_c: Pattern, x_L: Estimate) -> Estimate:
    """Paper operator: x = UR_gamma(x_hat) intersect x_L.

    The intersection restricts endpoints, not intermediate path states. An
    unobservable path can leave x_L and return, so a search confined to the
    induced subgraph G[x_L] would not implement this formula in general.
    This exact implementation may therefore inspect hidden states outside x_L.
    """

    return _unobservable_reach(plant, x_hat, gamma_c) & x_L


def limited_nx(plant: DFA, x: Estimate, sigma_o: str, x_L: Estimate) -> Estimate:
    """Paper operator: NX_sigma_o(x) intersect x_L; exactly one observable step.

    The caller supplies the preceding limited UR and checks that sigma_o is
    enabled by gamma. No hidden closure or second observable step is taken.
    """

    if sigma_o not in plant.observable:
        raise ValueError('limited NX requires one observable event')

    return frozenset(q_next for q in x for sigma, q_next in plant.enabled(q)
                     if sigma == sigma_o and q_next in x_L)


def limited_choice(plant: DFA, x_hat: Estimate, gamma_c: Pattern, x_L: Estimate) -> Choice:
    """Construct one local D-O-D fragment using the paper's truncated UR/NX."""

    x = limited_ur(plant, x_hat, gamma_c, x_L)
    gamma = gamma_c | plant.uncontrollable
    successors = []

    for sigma_o in sorted(gamma & plant.observable):
        x_hat_next = limited_nx(plant, x, sigma_o, x_L)

        if x_hat_next:
            successors.append((sigma_o, x_hat_next))

    return Choice(gamma_c, x, tuple(successors))


def complete_choice(plant: DFA, estimate: Estimate, pattern: Pattern) -> Choice:
    """Full UR/NX for execution and certification, without window truncation.

    Local LL-BTS fragments are built by limited_choice instead. This helper
    checks that a retained local fragment has not discarded physical outcomes.
    """

    gamma = pattern | plant.uncontrollable
    x = _unobservable_reach(plant, estimate, pattern)
    NX_sigma = defaultdict(set)

    for q in sorted(x):
        for sigma, q_next in plant.enabled(q):
            if sigma in gamma and sigma in plant.observable:
                NX_sigma[sigma].add(q_next)

    return Choice(pattern, frozenset(x),
                  tuple((e, frozenset(v)) for e, v in sorted(NX_sigma.items())))


def solve_limited_lookahead(pre: Preprocessing, estimate: Estimate | None=None,
                    horizon: int | None=None, *, full: bool=False,
                    certificates: bool=True, max_choices: int | None=None,
                    max_window_states: int | None=None,
                    timeout_seconds: float | None=None) -> Bipartitle_System:
    """Construct merged-estimate BTS and count-prune its greatest fixed point.

    Local fragments use limited_ur and limited_nx with the paper's explicit
    intersections with x_L. Full UR/NX are checked separately for certification:
    a truncated fragment alone must not certify an incomplete physical belief.
    Uncertified boundary choices are recorded for an optimistic second pass.
    Only if that second pass also loses do we report proved losing. Otherwise
    failure to find a sound controller is inconclusive, never 'no supervisor'.
    A pre-certified safe initial estimate stops before window enumeration;
    in that case result.window contains only materialized initial states.
    """

    started = perf_counter()
    tested = 0

    def check_budget(window_count):
        reason = ('choice budget exceeded' if max_choices is not None and tested >= max_choices else
                'window budget exceeded' if max_window_states is not None and window_count>max_window_states else
                'time budget exceeded' if timeout_seconds is not None and perf_counter()-started >= timeout_seconds else None)

        if reason:
            from des_core.offline_bts import BTSBudgetExceeded

            raise BTSBudgetExceeded(reason, seconds=perf_counter()-started,
                patterns_tested=tested, window_states=window_count, complete=False)

    plant = pre.plant
    x_hat_0 = frozenset({plant.initial}) if estimate is None else frozenset(estimate)

    if not x_hat_0 or not x_hat_0 <= plant.states:
        raise ValueError("estimate must be a nonempty subset of Q")

    u = pre.u if horizon is None else horizon

    if u < 0:
        raise ValueError("horizon must be nonnegative")

    # A proved forward-invariant all-live Qe needs no local window expansion.
    # Check BEFORE constructing Post_<=u: on a large known product that scan can
    # otherwise dominate work despite the already-complete safety certificate.
    if certificates and not full and x_hat_0 <= pre.Q_e:
        return Bipartitle_System('winning', x_hat_0, u, x_hat_0, {x_hat_0:()},
            frozenset((x_hat_0,)), 1, 0, 0, 0, perf_counter()-started,
            plant.controllable, {x_hat_0:()})

    # This window belongs to THIS solve call. Later estimates queued below do
    # not recenter it. A new call after an observation (e.g. through
    # Limited_Lookahead_Controller.solve) builds a new window around the updated belief.
    # Thus matching offline root patterns in one fixed window can need a
    # larger u than certifying a later, recentered observation estimate.
    x_L = set(plant.states) if full else set(x_hat_0)
    frontier = set(x_hat_0)

    if not full:
        for _ in range(u):
            targets = {t for q in frontier for _, t in plant.enabled(q)} - x_L
            x_L.update(targets)
            check_budget(len(x_L))
            frontier = targets

            if not frontier:
                break

    x_L = frozenset(x_L)
    Q_bad = pre.Q_d | (pre.Q_f if certificates else frozenset())
    Q_e = pre.Q_e if certificates else frozenset()
    # Decision nodes carry x_hat; observation nodes carry (x, gamma_c).
    # D_e are decision estimates contained in Q_e, with implicit enable-all.
    choices, D_e, boundaries = {}, set(), defaultdict(int)
    W_D, D_seen = deque([x_hat_0]), {x_hat_0}

    while W_D:
        x_hat = W_D.popleft()
        choices[x_hat] = []

        if x_hat & Q_bad:
            continue

        if x_hat <= Q_e:
            D_e.add(x_hat)

            continue  # implicit gamma=Sigma, no UR/NX or O node expansion

        for gamma_c in _patterns(plant):
            check_budget(len(x_L))
            # Paper construction: x = UR_gamma(x_hat) intersect x_L, followed
            # by x_hat_next = NX_sigma_o(x) intersect x_L for each observation.
            choice = limited_choice(plant, x_hat, gamma_c, x_L)
            tested += 1
            gamma = gamma_c | plant.uncontrollable

            if choice.closure & Q_bad or any(
                not any(e in gamma for e, _ in plant.enabled(q)) for q in choice.closure
            ):
                continue

            # Certification is separate from local graph construction. Check
            # the real physical outcomes before promoting a local fragment to
            # an executable policy; clipping alone does not prove safety.
            actual = complete_choice(plant, x_hat, gamma_c)

            if actual.closure & Q_bad or any(
                not any(e in gamma for e, _ in plant.enabled(q)) for q in actual.closure
            ):
                continue

            if choice != actual:
                boundaries[x_hat] += 1

                continue

            choices[x_hat].append(choice)

            for _, x_hat_next in choice.successors:
                if x_hat_next not in D_seen:
                    D_seen.add(x_hat_next)
                    W_D.append(x_hat_next)

    def prune(optimistic=False):
        remaining = {x_hat: len(v) + (boundaries[x_hat] if optimistic else 0)
                     for x_hat, v in choices.items()}
        incoming = defaultdict(list)

        for x_hat, options in choices.items():
            for i, choice in enumerate(options):
                for x_hat_next in {x_hat_next for _, x_hat_next in choice.successors}:
                    incoming[x_hat_next].append((x_hat, i))

        lost = {x_hat for x_hat, count in remaining.items() if not count and x_hat not in D_e}
        work, removed = deque(sorted(lost, key=lambda x_hat: sorted(x_hat))), set()

        while work:
            x_hat_next = work.popleft()

            for x_hat, i in incoming[x_hat_next]:
                if (x_hat, i) in removed:
                    continue

                removed.add((x_hat, i))
                remaining[x_hat] -= 1

                if not remaining[x_hat] and x_hat not in lost and x_hat not in D_e:
                    lost.add(x_hat)
                    work.append(x_hat)

        return lost, removed

    lost, removed = prune()
    policy = {x_hat: tuple(c for i, c in enumerate(v) if (x_hat, i) not in removed)
              for x_hat, v in choices.items() if x_hat not in lost}
    # Safe terminals have a compact implicit all-events policy. The helper below
    # computes complete observable updates only when execution needs them.
    status = 'winning' if x_hat_0 not in lost else (
        'inconclusive' if x_hat_0 not in prune(True)[0] else 'losing')
    observation_nodes = {(c.closure, c.pattern) for v in choices.values() for c in v}
    edges = {(x_hat, c.closure, c.pattern) for x_hat, v in choices.items() for c in v}
    obs_edges = {(c.closure, c.pattern, e, x_hat_next)
                 for v in choices.values() for c in v for e, x_hat_next in c.successors}
    result = Bipartitle_System(status, x_hat_0, None if full else u, x_L, policy,
                             frozenset(D_e), len(choices), len(observation_nodes),
                             len(edges) + len(obs_edges), sum(boundaries.values()),
                             perf_counter() - started, plant.controllable,
                             {x_hat: tuple(v) for x_hat, v in choices.items()})

    return result


def executable_choices(pre: Preprocessing, result: Bipartitle_System,
                       estimate: Estimate) -> tuple[Choice, ...]:
    if estimate in result.safe_terminals:
        return (complete_choice(pre.plant, estimate, pre.plant.controllable),)

    return result.policy.get(estimate, ())


def solve_offline(plant: DFA, estimate: Estimate | None=None) -> Bipartitle_System:
    """Full BTS baseline for the SAME deadlock-free objective and pruning code.

    Independently constructs the complete known-system UR/NX BTS, including
    unsafe branches, before count pruning. No Q_f/Q_e, horizon, or longest
    simple paths. Not a reproduction of Yin's other property specifications
    or the original quadratic pruning implementation.
    """

    from des_core.offline_bts import construct_offline_bts

    return construct_offline_bts(plant, estimate)


class Limited_Lookahead_Controller:
    """Re-solve with complete beliefs; retain a proved continuation as fallback.

    Receding fixed windows need not retain the previous proof's whole graph.
    A fresh inconclusive solve must not discard an already certified policy.
    The stored proof is query-local controller memory, not a synthesis cache.
    """

    def __init__(self, pre: Preprocessing, horizon: int | None=None):
        self.pre = pre
        self.horizon = pre.u if horizon is None else horizon
        self.estimate = frozenset({pre.plant.initial})
        self.proof = None

    def solve(self):
        fresh = solve_limited_lookahead(self.pre, self.estimate, self.horizon)
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


def validate_policy(pre: Preprocessing, result: Bipartitle_System) -> dict[str, int]:
    """Exhaustively verify every reachable state/observation of every policy choice."""

    if result.status != 'winning':
        return {'estimates': 0, 'choices': 0}

    queue, seen, count = deque([result.initial]), set(), 0

    while queue:
        x_hat = queue.popleft()

        if x_hat in seen:
            continue

        seen.add(x_hat)

        if x_hat <= pre.Q_e and x_hat in result.safe_terminals:
            assert all(pre.plant.enabled(q) and all(t in pre.Q_e for _, t in pre.plant.enabled(q))
                       for q in x_hat)

            continue

        options = executable_choices(pre, result, x_hat)
        assert options, ('missing control', x_hat)

        for choice in options:
            count += 1
            actual = complete_choice(pre.plant, x_hat, choice.pattern)
            assert actual == choice, ('incomplete estimate', x_hat)
            assert not actual.closure & pre.Q_d
            gamma = choice.pattern | pre.plant.uncontrollable
            assert all(any(e in gamma for e, _ in pre.plant.enabled(q)) for q in actual.closure)

            for _, x_hat_next in actual.successors:
                assert x_hat_next in result.policy or x_hat_next in result.safe_terminals, ('missing outcome', x_hat_next)
                queue.append(x_hat_next)

    return {'estimates': len(seen), 'choices': count}

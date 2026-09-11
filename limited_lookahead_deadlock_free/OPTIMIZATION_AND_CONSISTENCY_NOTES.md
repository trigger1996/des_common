# LL-BTS implementation and theory

## Scope and preserved semantics

The plant and its event partitions are unchanged. Example 1 has six states;
seven independent asynchronous copies have `6^7 = 279936` reachable states.
Every local state is reachable from `q_0`; interleaving those component paths
reaches every product tuple. The product is generated on demand, not enumerated.

`construct_ll_bts(..., pattern_mode="explicit")` retains the reference's
explicit decision nodes `D=(q_hat,x_hat)`, observation nodes `O=(x,gamma)`,
and transitions. Python patterns contain the controllable portion only:
`gamma_full = pattern | Sigma_uc`. Algorithm 2 returns **inclusion-maximal**
retained patterns, not just maximum-cardinality patterns.

UR is computed in the induced local graph on the fixed `x_L=Post_<=u(root)`;
NX retains successors in that window. A plant state whose outgoing edges all
leave the window is pending, not a concrete deadlock. Enabled observable events
without a local successor invalidate a choice, including at the boundary.
Every state in an observation estimate must have an enabled plant transition
under the control pattern. Uncontrollable events are never disabled.

## Reference optimizations integrated

The `[ref]des_core` implementation supplies transition indexing, event-partition
caching, UR caching by controllable hidden events, reuse of D->O computations
for equal estimates, one expansion per merged O node, reuse of constructed
control choices in Algorithm 2, grouped estimate analysis, integer hit tests,
count-based backward pruning, faster maximal-set extraction, and unique edge
counting. Separate `(q_hat,x_hat)` D nodes are still retained.

Example-2 physical-branch memory is preserved during render cleanup and reused
across runs. It affects visualization choices only, never synthesis. DFA input
transitions are copied into a read-only mapping so transition indexes cannot
silently become stale after caller mutation.

## Additional exact control-family optimization

The reference intentionally stops short of symbolic control families. The new
`reduced` and `factored` modes are additional representations, with the argument
below and differential tests. They are not literal enumerations of Algorithm 1.
The `explicit` mode remains available for comparison and small-case figures.

### Hidden choices

Fix the window and a reachable hidden closure `x`. Define

```
H_max(x) = Sigma_c,uo minus
           {e : some q in x has an e transition to x_L minus x}.
```

Every hidden pattern producing `x` is contained in `H_max(x)`. Adding the other
events in `H_max(x)` cannot leave `x` inside the local graph, so it preserves
the closure. Hidden edges leaving the window do not change local UR and can
only help the enabled-transition consistency test. Thus this is the unique
largest hidden choice for that closure. Any smaller surviving choice is
dominated by it. The generator branches only on unresolved hidden events that
can extend the reached set, then deduplicates completed closures. It does not
enumerate the global `2^|Sigma_c|` family.

`reduced` mode enumerates observable events occurring in each closure. Absent
observable events are always included, since they change neither successors
nor consistency and dominate their omission. Boundary observable events are
still relevant and are not silently included.

### Factored observable choices and backward pruning

For a fixed closure and its largest hidden choice, a family represents every
subset of controllable observable events. Its stored pattern is an **upper
bound**, not a safe control to execute. `synthesize_ll_bts_controls` dispatches
to the family-aware fixed point when `result.pattern_mode == "factored"`.

Given the currently surviving D estimates, include exactly the controllable
observable events whose occurring outcomes have a defined local successor and
whose successor estimate survives. Also include absent observable events.
Uncontrollable observable events must satisfy the same condition or the whole
family loses. Check that each concrete state still admits an enabled event.
If that check fails for the largest allowed observable choice, every smaller
choice also fails, so the whole family loses. Otherwise that choice dominates
every surviving observable subset in the family.

Losing a D estimate disables its controllable observable predecessor events,
or invalidates families having uncontrollable predecessors. Losing the last
family invalidates a D estimate. Repeat to the same greatest fixed point as
explicit Algorithm 2. Finally take inclusion-maximal patterns across the
surviving initial families. Consequently empty/nonempty synthesis, maximal
patterns, and observable physical successors agree with explicit enumeration.
This argument uses the optimistic treatment of pending states in the current
solver; it does not assert a global deadlock-freedom guarantee beyond its window.

In factored construction, locally decidable Algorithm-2 losses are processed
before expansion: missing uncontrollable observable outcomes invalidate a
family; missing controllable outcomes are disabled; if the largest remaining
pattern leaves some state without an enabled transition, the family is removed.
These losses cannot be repaired by later backward deletions, so this scheduling
change preserves the final synthesis fixed point and may avoid entire branches.

The `reduced` graph retains all D nodes and the union of concrete estimates.
The `factored` graph may search a strict subset because of early pruning.
O nodes and edges count **families/representatives**, not the full explicit
observation states and transitions. Reports label this distinction. The raw
`maximal_good_patterns` construction field is only a local classification
summary; executable controls always come from Algorithm 2.

## Timing and online execution

The default benchmark selects retained observable outcomes in deterministic
round-robin order and performs a fresh construction and synthesis every step.
`step_seconds` includes those computations; JSON records every step, not just
selected report rows. The target is at most 60 seconds per actual step on the
tested machine, not 60 seconds for the whole run.

An optional bounded cache stores only synthesis results, concrete search sets
and counts for identical roots within one immutable plant/horizon/mode run.
It is disabled by default. Cache hits and actual synthesis calls are separate.
Timing acceptance uses ordinary round-robin physical outcomes, not a forced
return cycle.

## Paper draft issues requiring author review

The source `__paper/main.tex` contains existing inconsistencies. These are not
silently interpreted as new optimization rules:

1. Algorithm 2 uses `not subseteq` in its maximality test and has an explicit
   Chinese comment saying not to change it. Literal use does not select maximal
   elements. The intended maximality condition used in both reference and new
   solvers is `not exists gamma' : gamma strict-subset gamma'`.
2. A chosen pattern should satisfy `gamma^(k) in Gamma^(k)*`; the draft uses
   equality between a pattern and a set of patterns.
3. The good/bad conditions in the draft are complementary and leave no pending
   case. The implementation's exact partition is: bad if the estimate meets
   concrete deadlocks; good if nonempty, nonbad, and every state has some
   successor in `x_L`; otherwise pending.
4. Global `UR(x_hat) intersect x_L` can include a path that exits and reenters
   the window. The implementation and the draft's local-knowledge prose use
   reachability in the induced local graph. The equations should explicitly
   write this restricted UR; they are not equivalent for arbitrary DFAs.
5. The consistency definition should explicitly require an enabled transition
   from every `q in x` under gamma. Otherwise disabling all controllable events
   can introduce a deadlock without violating the listed structural clauses.
6. Importing previous LL-BTS fragments is not implemented. The optional cache
   only reuses identical whole queries, with no cross-window fragment splicing.
7. The draft's old `5^8`, all-observable/all-uncontrollable, `u=7` statistics do
   not describe today's six-state inherited-partition example. Replace them
   with the new JSON/report results before publication. The old numbers must
   not be cited as evidence for the current model.

The paper source is left intact for author review, particularly the expressly
protected formula. Equivalence claims above concern the intended local
deadlock-free semantics and the reference implementation, not the literal
contradictory draft formulas.

## Validation

Run `python -m unittest discover -s tests -v`. Differential tests compare full
explicit enumeration, reduced enumeration and factored synthesis on 1,200
random plant/horizon combinations and 72 product/root/horizon combinations.
They check equal D nodes/search sets/local maximal-good summaries for `reduced`,
subset search for the early-pruned `factored` mode, and equal empty/nonempty
synthesis, maximal controls and all forward successors for both modes.
Additional tests cover boundary inconsistency, uncontrollable losses, selective
observable disabling, unique stored edges, immutable transition indexing,
event inheritance, branch-memory persistence, and cached/uncached trace equality.

The pre-edit backup was also checked on 240 example/root/horizon cases; final
synthesis results match both optimized modes. On a 4-copy initial-root `u=3`
comparison, construction plus synthesis took 10.44 s before the edits, 3.29 s
with optimized explicit enumeration, and 0.31 s with factored early pruning.
This is one measured query, not a claimed uniform speedup for all roots.
See `outputs/optimization_validation/comparison.json` and its replay script.

The accepted large run is 7 copies, `u=2`, a requested limit of 20 steps,
ordinary round-robin outcomes, and cache size zero. It completed 15 actual
synthesis attempts in 9.49 s (maximum step 5.29 s), then returned
`empty_synthesis`; the requested limit was not artificially enforced. It visited
497 unique concrete states of the 279936-state product. The 7-copy `u=3` trial
exceeded the 60-second first-step target and was stopped, so no completed-run
claim is made for that setting.

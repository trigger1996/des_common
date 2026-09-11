# Codex Memory

This file is project-local shared context for Codex sessions.

## 2026-09-11 cleanup and Example 2 revalidation

- README primary commands are the Example 2 import command and
  `python .\case1_product_benchmark.py --copies 8 --iterations 100 -u 3`.
  The four-copy command remains as a smaller alternative.
- Consolidated repeated physical branch artifact writing and removed redundant
  Example 3 output cleanup; synthesis algorithms and example plants are unchanged.
- Reran Example 2 against existing outputs, backed up under
  `outputs/example2_validation_20260911/before/`. All 59 output files remain;
  only runtime description and branch-choice memory changed. All PNG/GIF and
  transition/frame reports are byte-identical. See `comparison.json` alongside
  the backup. All image frames decoded successfully.
- All 30 unit tests passed. Example 2 matched the saved pre-optimization
  synthesis baseline for all 14 roots, horizons 0 through 6, and both explicit
  and factored modes (196 comparisons of emptiness, maximal patterns, successors).

## 2026-09-11 optimization update (supersedes older benchmark notes)

- Subsequent user correction: Example 1 now has `q_0 --o2--> q_1` and
  `q_2 --a--> q_0`; `q_1 --b--> q_2` is unchanged. Event partitions remain
  unchanged. Benchmark numbers recorded before this correction describe the
  old labels and must not be presented as measurements of the corrected plant.

- The user's timing target is **30--60 seconds per actual online synthesis
  step**, not a few seconds for the entire run. Validate fresh solves with
  cross-step result caching disabled and normal round-robin observable outcomes.
- Example 1 has six reachable states. Seven asynchronous copies have 279936
  reachable states. Preserve inherited controllability and observability; never
  replace the product alphabet with all-uncontrollable/all-observable events.
- Reference optimizations and Example-2 branch-memory fixes are integrated.
- `construct_ll_bts` defaults to `explicit` for small examples. The product
  runner defaults to `factored`: exact maximal hidden representatives and
  symbolic controllable-observable families, resolved by Algorithm 2.
  Do not execute raw family upper patterns. Do not report family counts as
  explicit O-node counts. Factored construction applies known inconsistent
  losses early, so concrete-state search can be a subset of explicit search.
- Read `OPTIMIZATION_AND_CONSISTENCY_NOTES.md` for the equivalence argument and
  unresolved draft notation issues, including the explicitly protected maximal
  pattern formula in `__paper/main.tex`. Paper text has not been silently fixed.
- README must retain these two user commands exactly:
  `python -c "from des_dfa_on_the_fly import main_example2_partial; main_example2_partial()"`
  and `python .\case1_product_benchmark.py --copies 4 --iterations 20 -u 3`.
- `requirements.txt` lists the runtime dependencies. Runners use the Agg backend
  for file output, so headless runs do not depend on Tk.
- DFA transition mappings are immutable copies; create a new DFA to change a
  plant instead of mutating transitions behind a cached index.

## Project

Workspace: `D:\__Workspace\Pycharm\des_common\on-the-fly_nonblocking`

Current active workspace is
`D:\__Workspace\Pycharm\ACC_LCSS-on-the-fly_nonblocking`.

This project demonstrates on-the-fly non-deadlock analysis for
discrete-event-system DFA examples.

## Paper Sprint Context

Target: LCSS submission due 2026-09-11. The intended manuscript is short
conference/letter style, about six pages.

Paper workspace:

- Main draft: `__paper/main.tex`
- Bib file: `__paper/ref_full.bib`
- Current generated PDF: `__paper/main.pdf`
- Local discussion/source PDFs in repo root:
  - `有限前视监督控制解法.pdf`
  - `查找有限前瞻控制.pdf`
- Reference PDFs are in `__ref/`, not `ref/`.

Writing direction for the current draft:

- Keep the existing line of thought: on-the-fly synthesis of deadlock-free DESs
  under partial observation through an incremental belief transition system
  (I-BTS).
- Introduction should mainly adjust the claimed contributions and organization,
  not rewrite the whole narrative.
- Preliminaries should be based on DFA + partial observation + simplified
  supervisory control. The current working assumption is all events are
  controllable, so control patterns can be taken as subsets of `Sigma`.
- Problem formulation should reflect the newer limited-lookahead/online
  supervisory-control motivation: the supervisor should decide from the current
  observation/information state using locally queried transitions instead of an
  offline complete observer.
- Later methodology/case sections are not finalized yet; avoid large edits
  there unless explicitly requested.

Definitions used by the current code:

- non-deadlock: a known state has at least one known outgoing transition
- deadlock: a known state has no known outgoing transition
- partial-observation risk: a belief is tagged `N` when at least one possible
  plant state is deadlocked

## Current Structure

```text
des_dfa_on_the_fly.py       # main runner
examples/
  non_deadlock.py            # active examples used by the runner
des_core/
  automata.py                # DFA and DESExample data structures
  deadlock.py                # snapshots, non-deadlock status, belief tags
  partial_observation.py     # unobservable closure and observable successors
  deadlock_semantics.py      # concrete and belief deadlock classification
  observer.py                # observer DFA construction for partial observation
  styles.py                  # visualization constants
  visualization.py           # NetworkX + Matplotlib PNG/GIF rendering
outputs/                     # generated PNG/GIF artifacts
```

## Run

```powershell
python des_dfa_on_the_fly.py
```

Dependencies:

```powershell
python -m pip install networkx matplotlib pillow
```

Quick compile check:

```powershell
python -m py_compile des_dfa_on_the_fly.py des_core\automata.py des_core\deadlock.py des_core\deadlock_semantics.py des_core\observer.py des_core\partial_observation.py des_core\visualization.py des_core\styles.py des_core\__init__.py examples\__init__.py examples\non_deadlock.py
```

## Current Examples

- `example1_symbolic_cycles_full`
- `example1_symbolic_cycles_full_partial_observation`
- `example2_nested_cycles_deadlock_full`
- `example2_nested_cycles_deadlock_full_partial_observation`
- `example3_possible_deadlock_full`
- `example3_possible_deadlock_full_partial_observation`

All plant states use `q_0`, `q_1`, ... naming. Events use single-letter names
such as `a`, `b`, `c`, and `o`.

`example2_nested_cycles_deadlock_full` has:

- singleton deadlock state: `q_12`
- outer cycle: `q_1 -> q_2 -> q_3 -> q_1`
- nested cycle: `q_2 -> q_4 -> q_5 -> q_2`
- deeper cycles: `q_6 <-> q_7` and `q_8 -> q_9 -> q_10 -> q_8`

## Tagged Observer State

Belief-state snapshots use labels of the form:

```text
{q_i,...}:Y
{q_i,...}:N
{q_i,...}:U
```

The fill color keeps the original graph-animation meaning. The border color
shows the tag: green for `Y`, red for `N`, gray for `U`.

`U` is a discovered but not-yet-expanded belief. When the frontier expands it,
the tag changes to `Y` if all plant states in the belief are non-deadlock, or
to `N` if at least one plant state is deadlocked.

Partial-observation output folders include `belief_state_observer_final.png`,
which is the complete belief observer graph from the last frame of
`belief_state_synthesis.gif`.

## Frame / Algorithm Alignment

Generated animations have two different frame semantics:

- `synthesis.gif` is from `make_on_the_fly_snapshots`. Frame 0000 is the
  initial known state, each intermediate frame is one discovered transition,
  and the last frame is the fixed point. These frames are not one-to-one with
  Algorithm 1's while-loop.
- `belief_state_synthesis.gif` is from
  `make_belief_state_synthesis_snapshots` and is the Algorithm 1 aligned
  animation. Frame 0000 is the initialized frontier; frame 00k is the yielded
  I-BTS after the k-th while-loop iteration; the final frame is the fixed
  point after the frontier becomes empty.

For `example3_possible_deadlock_full_partial_observation`, selected paper
frames align as:

- frame 0003 -> loop 3
- frame 0009 -> loop 9
- frame 0013 -> loop 13
- frame 0016 -> loop 16

Current output does not show a selected-frame sequence where a node is visibly
tagged `N` and then deleted in the next selected frame. Pruning is previewed in
the yielded frame title as `prune next: ...`, then applied immediately after
that capture, so the pruned belief is absent in the following frame.

Current generated frame counts:

- `example1_symbolic_cycles_full`: `synthesis.gif` 8 frames.
- `example1_symbolic_cycles_full_partial_observation`: `synthesis.gif` 9
  frames, `belief_state_synthesis.gif` 7 frames.
- `example2_nested_cycles_deadlock_full`: `synthesis.gif` 19 frames.
- `example2_nested_cycles_deadlock_full_partial_observation`: `synthesis.gif`
  19 frames, `belief_state_synthesis.gif` 13 frames.
- `example3_possible_deadlock_full`: `synthesis.gif` 25 frames.
- `example3_possible_deadlock_full_partial_observation`: `synthesis.gif` 52
  frames, `belief_state_synthesis.gif` 24 frames.

`example3_possible_deadlock_full_partial_observation` is the larger
possible-but-not-certain deadlock example. It has 15 plant states and includes:
an unobservable cycle through `q_4`, `q_5`, and `q_0`, nested observable cycles
through `q_2`, observable deadlock `q_9`, hidden deadlock `q_10` inside
unobservable reach, fully observable livelock `q_11`, and hidden livelock
`q_12 <-> q_13` inside unobservable reach. Additional return/exit edges are
`q_5 --u--> q_0`, `q_11 --u--> q_2`, `q_12 --a--> q_8`, and
`q_13 --a--> q_14 --a--> q_3`.

## Current LL-BTS / Limited-Lookahead Conventions

- Use LL-BTS / limited lookahead terminology, not BL-BTS / bounded lookahead.
- `\hat{\imath}` and `\imath` are information states; avoid calling them
  belief states in the paper text.
- The local transition-limited state set is denoted
  `Post_{\leq u}(q)`, not `Q_L(q,u)`.
- Main example lookahead limits are:
  - case 1 partial observation: `u=2`
  - case 2 partial observation: `u=4`
  - case 3 partial observation: `u=4`
- For paper case-study figures, case 3 should use online final LL-BTS frames,
  not construction-process `ll_bts_synthesis` frames or extracted
  `ll_bts_chain` previews. Each online frame is the completed LL-BTS for one
  selected iteration root.

## Case 3 Partial-Observation Motif

Case 3 should include a concrete partial-observation ambiguity where the
current physical state cannot be uniquely determined:

- an unobservable tail can contain two possible states, currently `q_4` and
  `q_5`;
- the same observable event `c` can move them to different concrete states:
  `q_4 --c--> q_15` and `q_5 --c--> q_16`;
- the resulting concrete states then merge through hidden behavior:
  `q_15 --u--> q_17` and `q_16 --u--> q_17`, followed by hidden continuation
  to `q_18`.

The intended entrance modification for case 3 is:

- start the plant from `q_2`;
- include `q_2 --u--> q_1`;
- include a visible transition from `q_1` to `q_0` using an observable event
  such as `b`;
- include `q_1 --u--> q_2`.

When this structure changes, rerun all examples with
`python des_dfa_on_the_fly.py` and check that case 3 partial observation still
has at least one LL-BTS maximal good control pattern.

## Large Product Benchmark

- `case1_product_benchmark.py` benchmarks an implicit asynchronous product of
  case 1 without constructing or drawing all product states.
- The default benchmark uses 8 copies of the 5-state case-1 component:
  `5^8 = 390625`, which exceeds `10^5`.
- It runs 200 local iterations with `u=7` and writes
  `outputs/case1_product_8copy_benchmark.txt`.
- It now calls the same complete core LL-BTS solver as the single-agent cases:
  `construct_ll_bts(product, current, horizon, store_edges=False)`. The
  `store_edges=False` setting skips storing large string edge labels but still
  generates the LL-BTS decision/observation information states and synthesis
  statistics.
- The detailed plot
  `outputs/case1_product_8copy_visited_states_with_new.png` should report
  concrete states obtained by splitting estimates in `\hat{\mathbb{I}}` and
  `\mathbb{I}`, plus separate curves for `|\hat{\mathbb{I}}|` and
  `|\mathbb{I}|`.
- The script prints one progress line per iteration. Use small checks such as
  `python case1_product_benchmark.py --copies 3 --iterations 3 -u 3`; non-default
  runs write parameterized filenames so they do not overwrite the default
  8-copy outputs.
- Product events are treated as observable and uncontrollable in this benchmark,
  giving one admissible all-event pattern. This avoids the independent
  `2^{|\Sigma_c|}` product control-pattern explosion while preserving the full
  LL-BTS information-state expansion.
- A 2026-09-10 one-iteration check with 8 copies and `u=7` took about 10.3 s
  and produced 13691 decision information states, 13691 observation information
  states, and 84075 LL-BTS edges. A 200-iteration full run is therefore much
  slower than the earlier `Post_{\le u}`-only benchmark.
- Do not use the normal visualization runner for 10^5-scale product systems;
  use the implicit product benchmark path and keep visualization disabled.

## Current Case 3 Outputs

Partial-observation case 3 now also writes:

- `original.png`
- `ll_bts_online_finals/index.txt`
- `ll_bts_online_finals/iteration_0000.png`
- `ll_bts_online_finals/iteration_0000.txt`
- additional `iteration_XXXX.png/.txt` pairs

Each `iteration_XXXX.png` is a completed LL-BTS final frame for one online
iteration root. LL-BTS case-study figures should not print `Y/N/U` tags; node
fill color distinguishes decision information states from observation
information states. The paired txt file contains the full transition relation
for that LL-BTS.

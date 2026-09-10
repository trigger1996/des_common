# DES DFA On-The-Fly Non-Deadlock Examples

This project contains Python examples for discrete-event-system (DES)
non-deadlock analysis on deterministic finite automata (DFA).

Definitions:

- non-deadlock: a state has at least one enabled outgoing transition
- deadlock: a state has no enabled outgoing transition
- partial-observation non-deadlock risk: a belief is unsafe when at least one
  possible plant state is deadlocked

## Structure

```text
des_dfa_on_the_fly.py       # runner for all examples
examples/
  non_deadlock.py            # non-deadlock examples
des_core/
  automata.py                # DFA and example data structures
  deadlock.py                # non-deadlock snapshots and belief tags
  implicit_product.py        # on-demand asynchronous product benchmark tools
  ll_bts.py                  # limited-lookahead information-state construction
  observer.py                # partial-observation observer construction
  partial_observation.py     # unobservable closure and observable successors
  deadlock_semantics.py      # concrete and belief deadlock classification
  pruning.py                 # pruning-aware deadlock branch removal
  styles.py                  # visualization style constants
  visualization.py           # NetworkX + Matplotlib rendering
outputs/
  <example_name>/
    original.png
    overall_connection.gif
```

## Examples

The runner renders three full-observation plants and their partial-observation
versions:

1. `example1_symbolic_cycles_full`
   A small symbolic plant using states `q_0` ... `q_4` and events `a` ... `f`.
   It has two cycles sharing `q_1`, and every state is non-deadlock.

2. `example1_symbolic_cycles_full_partial_observation`
   Partial-observation version of example 1. Events `c` and `f` are
   unobservable.

3. `example2_nested_cycles_deadlock_full`
   A larger symbolic plant using states `q_0` ... `q_12` and events
   `a` ... `o`. It has one singleton deadlock state, `q_12`, plus multiple
   cycles:
   - outer cycle: `q_1 -> q_2 -> q_3 -> q_1`
   - nested cycle: `q_2 -> q_4 -> q_5 -> q_2`
   - deeper cycles: `q_6 <-> q_7` and `q_8 -> q_9 -> q_10 -> q_8`

4. `example2_nested_cycles_deadlock_full_partial_observation`
   Partial-observation version of example 2. Events `d`, `g`, `j`, `l`, and
   `n` are unobservable.

5. `example3_possible_deadlock_full`
   A single-agent partial-observation case study. The plant starts from `q_2`,
   with hidden entrance ambiguity `q_2 --u--> q_1` and `q_1 --u--> q_2`, plus
   the observable transition `q_1 --b--> q_0`. It combines nested observable
   cycles, an observable deadlock `q_9`, a hidden deadlock `q_10`, a fully
   observable livelock `q_11`, and a hidden livelock region `q_12-q_13`.
   The plant event partition is `Sigma_o={a,b,c}`, `Sigma_uo={u,v}`,
   `Sigma_c={a,c,u}`, and `Sigma_uc={b,v}`.
   The partial-observation ambiguity motif is:
   `q_4 --c--> q_15`, `q_5 --c--> q_16`, followed by hidden merge
   `q_15 --u--> q_17` and `q_16 --u--> q_17`.

6. `example3_possible_deadlock_full_partial_observation`
   Partial-observation version of example 3. Its unobservable closures expose
   both hidden deadlock risk and hidden livelock behavior.

7. Large-scale case-1 product benchmark
   `case1_product_benchmark.py` builds an implicit asynchronous product of
   eight copies of the 5-state case-1 component. The concrete product has
   `5^8 = 390625` plant states, exceeding `10^5`, but the benchmark never
   enumerates or visualizes the full product. Each iteration runs the same
   complete LL-BTS core solver used by the single-agent examples, with the
   current local `Post_{\le u}` window as its transition limit. The default run
   uses 200 iterations and `u=7`.

## Tagged Observer State

Belief-state animations use observer states:

```text
i = (X, tag)
X in 2^Q
tag in {Y, N, U}
```

The node label is rendered as `{q_i,...}:Y`, `{q_i,...}:N`, or `{q_i,...}:U`.
The node fill color keeps the original visualization meaning. The node border
color shows the tag:

- green border: `Y`, expanded and non-deadlock
- red border: `N`, expanded and contains a deadlock risk
- gray border: `U`, discovered but not expanded yet

For plant-level partial-observation animations, orange marks concrete states
inside the current belief that are semantically deadlocked. This distinguishes
possible deadlock from certain deadlock under partial observation.

## Paper Algorithm Code Map

The implementation entry for the current limited-lookahead construction is:

```python
construct_ll_bts(plant, current_state, horizon, store_edges=True)
```

in `des_core/ll_bts.py`.

The main pieces are:

- Lookahead window `Post_{\le u}(\hat q_0)`:
  `des_core/limited_lookahead.py::post_leq`
- Admissible control patterns `Gamma`:
  `des_core/ll_bts.py::admissible_control_patterns`
- Controlled unobservable reach `UR_gamma(x) cap x_L`:
  `des_core/ll_bts.py::controlled_unobservable_reach`
- Observable successor `NX_sigma(x) cap x_L`:
  `des_core/ll_bts.py::observable_next`
- Decision and observation information states:
  `des_core/ll_bts.py::DecisionState` and `ObservationState`
- LL-BTS rendering snapshots:
  `des_core/ll_bts.py::make_ll_bts_synthesis_snapshots`

The large-scale product benchmark calls the same `construct_ll_bts` function
with `store_edges=False`. This skips storing large string labels for every edge
but still executes the same LL-BTS decision/observation state generation,
classification, and maximal-pattern synthesis path.

The `Y/N/U` tags classify local information states: `Y` is locally verified,
`N` exposes a deadlock witness, and `U` is pending within the current
lookahead window.

## Frame / Iteration Alignment

There are two generated animations, and they use different frame semantics.

`overall_connection.gif` is the plant/observer edge-discovery animation from
`make_on_the_fly_snapshots`. Its frame 0000 is the initial known state, each
intermediate frame records one newly discovered transition, and the last frame
records the fixed point. These frames do not correspond one-to-one to
Algorithm 1's `while F^(k) != empty` loop.

`ll_bts.gif` is the LL-BTS snapshot from
`make_ll_bts_synthesis_snapshots`. It shows the local decision and observation
information states generated under the configured lookahead limit.

The old chain-frame output was only a path-preview layout for reading a
`D -> O -> D -> O` slice of the same LL-BTS. The default LL-BTS renderer now
uses that wider path-preview layout directly, so separate chain-frame files are
not generated by the runner.

For the case-study example
`example3_possible_deadlock_full_partial_observation`, the useful output is no
longer the construction animation or the extracted chain preview. The runner
now writes one completed LL-BTS final frame for each selected online iteration
root:

```text
outputs/example3_possible_deadlock_full_partial_observation/
  original.png
  ll_bts_online_finals/
    index.txt
    iteration_0000.png
    iteration_0000.txt
    ...
```

Each `iteration_XXXX.png` is the full LL-BTS after that online iteration's
local construction has completed. The matching `iteration_XXXX.txt` lists the
decision information states, observation information states, `D->O`
control-pattern transitions, and `O->D` observable transitions. LL-BTS
case-study figures do not print `Y/N/U` tags; node fill color distinguishes
decision information states from observation information states.

Current generated frame counts:

| Example | `overall_connection.gif` alignment | `ll_bts.gif` alignment |
| --- | --- | --- |
| `example1_symbolic_cycles_full` | 8 frames: 0000 initial, 0001-0006 edge discoveries, 0007 fixed point | not generated |
| `example1_symbolic_cycles_full_partial_observation` | not generated by default | one LL-BTS snapshot with `u=2` |
| `example2_nested_cycles_deadlock_full` | 19 frames: 0000 initial, 0001-0017 edge discoveries, 0018 fixed point | not generated |
| `example2_nested_cycles_deadlock_full_partial_observation` | not generated by default | one LL-BTS snapshot with `u=4` |
| `example3_possible_deadlock_full` | 25 frames: 0000 initial, 0001-0023 edge discoveries, 0024 fixed point | not generated |
| `example3_possible_deadlock_full_partial_observation` | not generated by default | online final frames in `ll_bts_online_finals/` |

## Run

```powershell
python des_dfa_on_the_fly.py
```

Partial-observation folders other than the case-study example also contain:

```text
ll_bts.gif
ll_bts_final.png
ll_bts_transition_report.txt
```

For `example3_possible_deadlock_full_partial_observation`, the runner instead
writes online final-frame reports:

```text
ll_bts_online_finals/index.txt
ll_bts_online_finals/iteration_0000.png
ll_bts_online_finals/iteration_0000.txt
...
```

Each txt records the complete transition relation of that iteration's completed
LL-BTS final frame.

For the large-scale case-1 product benchmark, run:

```powershell
python case1_product_benchmark.py
```

The default command runs 8 copies, 200 online iterations, and overall
lookahead limit `u=7`. It prints one progress line per iteration:

```text
[   1/200]   0.50% elapsed=    10.3s |Ihat|=  13691 |I|=  13691 D-est=  13691 O-est=  13691 new=  13691 cum=  13691 (  3.5%) edges=   84075
```

The fields are `|\hat{I}|`, `|I|`, concrete states obtained by splitting the
decision-state estimates, concrete states obtained by splitting the
observation-state estimates, newly discovered unique concrete states,
cumulative unique concrete states, and LL-BTS edge count.

For a short console/PyCharm check, use smaller parameters:

```powershell
python case1_product_benchmark.py --copies 3 --iterations 3 -u 3
```

To run the default benchmark from PyCharm, create a Python run configuration
with script path `case1_product_benchmark.py`, working directory set to the
repository root, and optional parameters such as `--iterations 20 -u 7`.

This writes:

```text
outputs/case1_product_8copy_benchmark.txt
outputs/case1_product_8copy_visited_states.png
outputs/case1_product_8copy_visited_states_with_new.png
outputs/case1_product_8copy_visited_states_paper.pdf
```

Non-default parameter choices write files with a parameterized stem such as
`case1_product_3copy_u3_3iter_visited_states.png`, so quick tests do not
overwrite the default 8-copy outputs.

The default 8-copy plot uses a single axis with iteration number on the x-axis
and visited state count on the y-axis. The detailed `_with_new` plot shows
states appearing inside decision-state estimates, states appearing inside
observation-state estimates, `|\hat{\mathbb{I}}|`, `|\mathbb{I}|`, newly
discovered unique concrete states, and a dashed reference line for
`|Q_product| = 5^8 = 390625`. The PDF plot uses larger fonts for IEEE
double-column placement.

The product benchmark treats product events as observable and uncontrollable,
so the admissible control-pattern set has one pattern containing all product
events. This keeps the large-scale run focused on the complete LL-BTS
information-state construction instead of the independent
`2^{|\Sigma_c|}` control-pattern explosion. Under this benchmark setting, each
decision information state induces exactly one observation information state;
therefore `|\hat{\mathbb{I}}|` and `|\mathbb{I}|` are equal. They may differ
when multiple control patterns are retained or when unobservable tails merge
several decision-state estimates into the same observation state.

A more control-faithful product benchmark can preserve the component event
partition: copied events are observable exactly when their component event is
observable, unobservable otherwise, and controllable exactly when their
component event is controllable. This is the strict product interpretation, but
it makes the control-pattern set scale as `2^{copies * |Sigma_c|}`. A practical
middle ground for large-scale tests is synchronized control-pattern selection:
the supervisor enables component event names globally across all copies, while
the plant still evolves asynchronously. This gives `2^{|Sigma_c|}` control
patterns instead of `2^{copies * |Sigma_c|}` and keeps the observation model
closer to the component DFA.

The product used here is asynchronous/interleaving, not synchronous. A product
state is a tuple of component states, but one transition updates only one
component, with event labels such as `a_0` or `u_3`. In the inherited
observability interpretation, `a_i` is observable exactly when component event
`a` is observable, while `u_i` is unobservable exactly when component event `u`
is unobservable. This is different from synchronous tuple events such as
`(a,u,b,...)`, where a tuple event is often treated as unobservable only if all
component events in the tuple are unobservable.

## Dependencies

```powershell
python -m pip install networkx matplotlib pillow
```

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
  observer.py                # partial-observation observer construction
  partial_observation.py     # unobservable closure and observable successors
  deadlock_semantics.py      # concrete and belief deadlock classification
  pruning.py                 # pruning-aware I-BTS deadlock branch removal
  styles.py                  # visualization style constants
  visualization.py           # NetworkX + Matplotlib rendering
outputs/
  <example_name>/
    original.png
    synthesis.gif
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
   A 15-state plant combining an unobservable cycle, nested observable cycles,
   an observable deadlock `q_9`, a hidden deadlock `q_10`, a fully observable
   livelock `q_11`, and a hidden livelock region `q_12-q_13`. It also includes
   observable return edges `q_5 -> q_0` and `q_12 -> q_8`, plus an unobservable
   return edge `q_11 -> q_2`.

6. `example3_possible_deadlock_full_partial_observation`
   Partial-observation version of example 3. Its unobservable closures expose
   both hidden deadlock risk and hidden livelock behavior.

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

## Paper Algorithm 1 Code Map

The closest implementation entry for Algorithm 1, "On-the-fly deadlock-free
construction of I-BTS", is:

```python
make_belief_state_synthesis_snapshots(plant, observable)
```

in `des_core/deadlock.py`.

Algorithm 1 is implemented across the following functions:

- Main loop `while F^(k) != empty`:
  `des_core/deadlock.py::make_belief_state_synthesis_snapshots`
- `Expand(i)`, the local unobservable reach / closure:
  `des_core/deadlock.py::close_unobservable`
- `Update(i, I^(k))`, adding newly discovered belief states:
  `des_core/deadlock.py::remember`
- Construction of the I-BTS transition function `delta_T`:
  `des_core/deadlock.py::add_ibts_transition`
- Observable successors `NX_sigma(x)`:
  `des_core/partial_observation.py::observable_successors`
- `Prune(T^(k), D)`:
  `des_core/pruning.py::prune_deadlock_branches`
- Open / closed belief-state test, including pruning-aware closed states:
  `des_core/pruning.py::is_closed_after_pruning`
- Yielding the current `T^(k+1)` for GIF and frame rendering:
  `des_core/deadlock.py::capture`

The `Y/N/U` tags are deadlock-classification tags, not open/closed tags.
Open/closed is used internally by pruning: an open belief is kept because
future exploration may still discover successors; a closed deadlock or
backward-losing belief can be safely pruned.

## Run

```powershell
python des_dfa_on_the_fly.py
```

Partial-observation folders also contain:

```text
belief_state_synthesis.gif
belief_state_observer_final.png
```

## Dependencies

```powershell
python -m pip install networkx matplotlib pillow
```

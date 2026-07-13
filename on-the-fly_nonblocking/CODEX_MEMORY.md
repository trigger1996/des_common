# Codex Memory

This file is project-local shared context for Codex sessions.

## Project

Workspace: `D:\__Workspace\Pycharm\on-the-fly_nonblocking`

This project demonstrates on-the-fly non-deadlock analysis for
discrete-event-system DFA examples.

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

`example3_possible_deadlock_full_partial_observation` is the larger
possible-but-not-certain deadlock example. It has 15 plant states and includes:
an unobservable cycle `q_4 <-> q_5`, nested observable cycles through `q_2`,
observable deadlock `q_9`, hidden deadlock `q_10` inside unobservable reach,
fully observable livelock `q_11`, and hidden livelock `q_12 <-> q_13` inside
unobservable reach. Additional return edges are `q_5 --m--> q_0`,
`q_12 --l--> q_8`, and `q_11 --z--> q_2` where `z` is unobservable.

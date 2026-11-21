# DIRM opacity theory

The proof-oriented discussion of DIRM history compression, opacity on the
Y-Z-W/I-J-L structure, consistency, synthesis soundness, and conditional
completeness is in
[`TECHNICAL_DISCUSSION_HISTORY_OPACITY_TTS.md`](%5Bpaper%5Denforcement_dynamic_information_release/TECHNICAL_DISCUSSION_HISTORY_OPACITY_TTS.md).
The remaining proof and implementation tasks are tracked in
[`TODO_HISTORY_OPACITY_TTS.md`](%5Bpaper%5Denforcement_dynamic_information_release/TODO_HISTORY_OPACITY_TTS.md).

This repository now keeps two **coexisting theory tracks**:

- `opacity_iwa/`: the existing timed IWA / UR / NX research implementation.
- `dirm/`: a compact, dependency-free implementation for a general partial DFA.

`dirm` follows Hou, Yin and Li, “A framework for current-state opacity under
dynamic information release mechanism”, *Automatica* 140 (2022).  It implements
the augmented DFA, `UR_tilde`, `UR_tilde_L`, `NX_tilde`, `NX_tilde_r`,
`NX_tilde_{sigma,r}`, the three-component
DIRM-observer, and the reachability test of current-state opacity.

The implementation mirrors that construction directly:

1. `dirm/dfa.py` defines a partial general DFA.
2. `dirm/augmented.py` adds the pending-release bit and implements the paper's
   tilde operators using the state-dependent sets `O(x_tilde)` and
   `O_L(x_tilde)`.
3. `dirm/observer.py` builds the paper's reachable triples
   `(x_tilde, q_hat, q)`.
4. `dirm/verification.py` applies the paper's opacity reachability criterion.

The observer transition is the paper's Eq. (4)--(5): on a true information
release it switches the low-level estimate to the high-level intermediate
estimate before taking `UR_tilde_L`.  `tests/test_dirm_paper_example.py` checks the
published Example 6 prefixes `epsilon`, `h`, `hh`, and `hha` component by
component.

## Minimal use

```python
from dirm import DFA, DIRMObserver

plant = DFA.build(
    states={"0", "1", "2"}, alphabet={"a", "h", "u"}, initial="0",
    transitions={("0", "h"): "1", ("1", "u"): "2"}, secret_states={"2"},
)
observer = DIRMObserver(
    plant, observable={"a"}, unobservable={"u"}, releasable={"h"}, release_states={"2"},
)
result = observer.check_current_state_opacity()
print(result.opaque, result.witness)
```

## Observer graph and state listing

Run the paper example exporter with:

```powershell
python dirm_demo_main.py
```

It writes `outputs/dirm_example_3_observer.png` and
`outputs/dirm_example_3_observer.txt`. The PNG uses rounded rectangles;
each `S<number>` maps to the complete observer triple and all event-labelled
transitions in the TXT file.  For any other plant, call
`dirm.export.export_observer(observer, directory, stem)`.

The event sets must be a disjoint partition of the DFA alphabet.  In accordance
with the paper's simplifying assumption, a releasable event cannot enter a release
state directly.

## Preserved IWA examples

`opacity_iwa/` was consolidated to two non-interchangeable theory engines:

- `t_aic_1.py` (`TimedBipartiteSystem`, compatibility alias `t_bts`) preserves
  the original `IWA_4.3` construction.
- `t_aic_2.py` (`WeightedAllInclusiveController`, compatibility alias `w_aic`)
  supports interval endpoint attributes and matches the
  explicit state-estimate partition in `Enforcement_IWA.pdf`, Example 4.

The remaining historic variants and all `old/` / `draft/` files are archived in
`backups/opacity_iwa_before_consolidation.zip`. They were not retained in the
active source tree because their outputs are superseded or duplicate one of the
two maintained semantics.

The two IWA theory examples remain available:

```powershell
python tac2023_demo_main.py
python tac2023_r1_demo_main.py
```

They use the local IWA YAML reader and a small NetworkX legacy-API adapter, so
they do not require PyYAML and continue to run with NetworkX 3.x.

Run the DFA/DIRM regression tests with:

```powershell
python -m unittest discover -s tests -v
```

This also runs IWA regression checks for the two documented baselines and the
three Example 4 state estimates from `Enforcement_IWA.pdf`.

## Supervisory DIRM-TTS

The paper's control/observation/release states map to the code classes
`IState`/`JState`/`LState`, respectively.

`dirm/supervisory.py` adds control-dependent information-state construction
and greatest-fixed-point safety synthesis. It implements the tripartite
observation-based evolution from `DIRM监督控制二分图.pdf`:

- `I -> J -> I'` after an ordinary instant `Sigma_o` observation;
- `I -> J -> L -> I'` after an information release.

A code-level `I` state is one `(q_hat, q)` pair and a `J` state adds the selected control
pattern `gamma`, so `J` belongs to
`2^X_tilde x 2^X_tilde x Gamma`. Neither contains an exact plant state. `L`
is the paper-aligned `(q_mid, gamma)` post-release/pre-closure state. The
augmented `N/Y` bit
remains inside estimates because it affects whether a later transition releases
information; it is not an exact-state field.

After construction, a dominance reduction removes a smaller control pattern
`gamma_1` when it has the same predecessor `I`, the same two `J` estimates, and
the same complete ordinary/release successors as a proper superset
`gamma_2`. The larger pattern is retained because it is behaviorally identical
at that information state and is more permissive. Unreachable `J/L` states are
then pruned.

The controlled `UR_tilde` operators retain the paper's state-dependent
observability test.  A transition is included in the closure exactly when its
event is enabled by the current control pattern and is outside `O(x_tilde)`
(or `O_L(x_tilde)` for the low-level estimate).  Thus an event in `Sigma_uo`
is not swallowed by the closure when its successor is a true release state.

The maintained TAC 2025 example is defined in
`dirm/dfa_tac2025_example.py`. Its user examples use states `0` through `6`
and release states `2` and `5`, with
releasable events `h1` and `h2`. Controllability and DIRM visibility remain
independent event partitions.

Build and synthesize all six maintained examples with:

```powershell
python dirm_supervisory_demo.py
```

Each run prints the secret DFA/augmented states and the DI-TTS classifications,
and writes the same classification report to `outputs/<stem>_diagnostics.txt`.
The complete `<stem>.txt` listing includes these reports, per-state removal
rounds and reasons, and the IDs of successors responsible for removal. IDs
are identical in the PNG, TXT, and console output.

Secret DFA states are drawn with red double borders and pink fill; augmented
secret states have red borders and explicit `SECRET` labels (green fill still
indicates a release state). DI-TTS figures distinguish:

- Red solid: secret-revealing J-states (nonempty, entirely secret low-level estimate).
- Orange dashed: states removed during consistency pruning, with the round shown.
- Purple dotted: secret-only I/L estimates removed directly by the existing safety
  solver, listed separately from secret-revealing J-states and consistency removals.
- Normal I/J/L colors: states retained in the winning region.

Inconsistency is evaluated during pruning: an I-state has no remaining control
successor, a J-state has lost a required observation/release successor, or an
L-state has lost its required return. The recorded causes and rounds refer to
these intermediate retained structures, rather than the original full graph.
These diagnostics do not change the winning region or synthesized policy.

The common `main()` runs `example_5()` first, followed by `example_1()` through `example_4()`.
Example 1 is the corrected user-provided example: only event `a` remains on
`q_2 -> q_3`. Example 2 preserves both
`q_1 --b--> q_3` and `q_1 --a--> q_2 --a--> q_3`, plus the branch
`q_0 --uc--> q_6 --o--> q_2` and the cycle
`q_3 --uc--> q_4 --b--> q_5 --o--> q_3`, with an additional
`q_4 --a--> q_6` branch. The cycle `q_4 --a--> q_6 --h--> q_4`
contains a releasable event. Example 2 uses `q_2` and `q_5` as release
states and `q_5` and `q_6` as nonadjacent secret states. Events `a`, `b`, and
`h` are controllable; `o` and `uc` are uncontrollable. Only `o` is observable,
`h` is releasable, and `a`, `b`, and `uc` are unobservable. The shared `o` observation from `q_5`
and `q_6` yields the winning I-state `({2N,3N},{2N,3N})`.
The uncontrolled plant is not DIRM opaque: `uc h a h b` reaches the
low-level estimate `{5Y}`. The supervisory TTS contains 41 states and has
a winning initial state. Example 3 is maintained as an independent
project example and contains the revised edge `q_9 --a--> q_3`.
Its release states are `q_5` and `q_9`, and its only secret state is `q_7`.
The `q_3 --u--> q_5` branch releases pending `h` information, while
`u h u a` shows that the uncontrolled plant is not DIRM opaque.
Only `a` is controllable. Its TTS has 30 states and a winning I-state
with two states in each estimate.

Example 4 is an independent seven-state example. Its central branch contains
`q_3 --h--> q_5` and `q_6 --a--> q_3`. Both lower branches enter `q_6`, which
carries a single `u` self-loop. Its release states
are `q_3` and `q_6`.

Example 5 uses the topology of Fig. 1 in Hou, Yin and Li's DIRM paper. The
original `a` is unobservable; the two edges entering states 4 and 9 are
relabeled `o` and are observable. The release states remain `{1, 4, 8}` as in
the source figure. As in the manuscript, only `a` is controllable;
`h`, `o`, and `u` are uncontrollable, so every control pattern includes `o`.
The branches `h a h o` and `u h a h o` both have static
projection `o`. State 1 releases the first branch's initial `h`; state 8
releases both `h` events of the second branch. At the final `o`, the first
branch enters 4Y and releases its remaining `h`, while the second moves from
8Y to 9N without a new release. Both final DIRM projections are `hho`, but
their histories differ: `{epsilon, h, hho}` versus `{epsilon, hh, hho}`.

Example 6 is the six-state high-level-estimate counterexample. Its transitions
are `0-h-1`, `1-o1-2`, `1-o2-3`, `2-h-3`, `3-h-2`, `2-o3-4`, and `3-o3-5`.
Events `{o1,o2,o3}` are observable and `h` is releasable; all events are
uncontrollable. Release states are `{4,5}` and only state 4 is secret.
After `h o1` and `h o2`, the two J-states have the same low estimate `{2Y,3Y}`
and the same full control pattern, but high estimates `{2Y}` and `{3Y}`.
An immediate `o3` release gives `{4Y}` and `{5Y}`, respectively. Additional
hidden `h` events alternate the two outcomes, which the release-language
regression checks by parity. The initial state is losing because none of
the events can be disabled. This is project Example 6, distinct from the
published paper's Example 6 mentioned above.

Use `from dirm import build_example_6_bts`, or run only its exporters with
`python -c "from dirm_supervisory_demo import example_6; example_6()"`.
The outputs are `outputs/dirm_supervisory_example_6{,_plant,_augmented}.txt`
and the matching PNG files, plus the diagnostics listing.

The Example 5 challenge also runs two independent Y/Z AIC/BTS syntheses
through `dirm_supervisory_demo.py`. The high comparison uses the original
plant. The low comparison calculates on the augmented plant but displays only
original state numbers. It uses DIRM low UR, while ordinary and release
successors are merged under the same observed event in NX. See
[`bts_comparasion/README.md`](bts_comparasion/README.md).

Each example writes three PNG/TXT pairs under `outputs/`: the original DFA
plant, its reachable DIRM augmented system, and the supervisory tripartite
graph. Examples 1 and 2 share the user-example layout and mark secret states with red
double circles.

# Example 5: single-estimate AIC/BTS comparisons

These are two applications of the Y/Z bipartite transition system in Yin and
Lafortune, *A Uniform Approach for Synthesizing Property-Enforcing Supervisors
for Partially-Observed Discrete-Event Systems*. Every Y-state is one estimate
`Q`; every Z-state is `(Q, gamma)`. The graph is pruned into an opacity-safe
All Enforcement Structure (AES).

Both baselines use the manuscript's event partition: only `a` is
controllable, so the full control patterns are `{h,o,u}` and `{a,h,o,u}`.
Event `o` cannot be disabled. In the high baseline, `{h,o}` is the fixed
observable set used for comparison; it treats the releasable `h` as
immediately observable. The actual DIRM observable set is `{o}`.

| Baseline | Internal state space | UR/NX behavior |
| --- | --- | --- |
| `high` | Original plant `X` | Ordinary UR/NX; `{h,o}` observable |
| `low` | Augmented plant `X̃` | DIRM low UR; `h` release labeled `h`, ordinary and release `o` successors merged |

The high graph displays original states. The low graph calculates on augmented
states internally but projects away `N`/`Y` for display. Its full-control path is
`{0} --UR--> {0,5,6,7} --h--> {1,8} --UR--> {1,2,3,8} --o--> {4,9}`.
There is no separate release edge: ordinary `o` and `o/release` targets share
one `o` successor. State 9 then appears to conceal secret state 4. The low
graph deliberately loses the distinction between the two release histories;
its one-estimate AES is a comparison construction, not a proof of DIRM opacity.

The independent IJL supervisory DIRM graph in `outputs/dirm_supervisory_example_5.*`
retains both estimates and explicit release updates. Run
`python dirm_supervisory_demo.py` to export all three graphs.

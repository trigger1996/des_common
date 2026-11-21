# Codex Memory

This file is project-local shared context for Codex sessions.

## Latest clarification: u5 safety versus initial fixed-window root matching

- User requested consolidating the two explanations into earlier annotations.
  Shared paper_example_models.u5_u6_annotation() now feeds运行结果.md and
  PAPER_EXAMPLES_RERUN.md; active main.tex has equivalent English explanation.
- u5 already guarantees deadlock-free operation for the certified policy that
  initially disablesb (root{a,o2},full6-state/7-edge reachable closed loop).
  u6 restores offline initial root{a,b,o2} within ONE solve call centered atq0.
- solve_limited_lookahead builds one window per call; queued future decision estimates
  share it. Limited_Lookahead_Controller after observation calls again around the updated
  complete belief, retaining certified continuation. Do NOT claim receding
  replanning intrinsically requiresu6.
- Counterfactual initialb: firsto1 has NX={q6,q8,q11},not knownq8. Next mode{a}
  disablesb/o2; UR={q6,q7,q8,q9,q10,q11}. A NEW solve from that estimate atu5
  includesq10 and iswinning. Regression test verifies fixed-vs-recentered windows.
- A later winning solve alone is not a whole cross-step safety proof; parameter
  u5 alone does not license arbitrary control choices. Current u5 safety is tied
  to the certified strategy, whose actual initialb isdisabled.
- Code comments, README/guide, manuscript/PDF and75-file review snapshot updated.
  75 tests pass. Recompiled7-page PDF: no undefined references/controls/overfulls.

## Latest: separate UR and single-event NX in the offline baseline

- User requested clearer UR/NX separation. des_core/offline_bts.py now exposes
  traditional_ur(plant,estimate,pattern): zero or more enabled hidden steps,
  and traditional_nx(plant,states,observable_event): exactly one specified
  observable event, without a further UR or any second observable transition.
- traditional_ur_nx stays compatible: full UR then private _traditional_nx_all
  batches independent NX_event results in one edge scan. This avoids making
  the offline baseline rescan all transitions for every observable symbol.
- NX may union targets from several possible sources; the map of NX sets is
  alternatives, not a multi-observable execution. Next UR belongs to the next
  decision and its newly chosen control pattern. Standalone NX does not impose
  a control pattern; the caller filters enabled observable events.
-74 tests pass. Reconstructed all61 offline systems and checked exact statuses,
  D/O/edge counts and root maximal patterns against saved BTS exports: unchanged.
  Updated README, code-review guide and source snapshot; historical timing data
  was not rerun or relabelled as new measurements after this refactor.

## Latest: bilingual report, paper reruns, manuscript sync and code-review output

- Four requested运行结果.md headings now have English counterparts. Main table
  uses Chinese header, Markdown delimiter, then bold English counterpart row;
  this preserves valid GFM. Negative-savings paragraph includes14/0/0 main cases
  and170 negative-memory random cases. Generators preserve the additions.
- User explicitly requested rerunning active article examples and reviewing code.
  paper_example_models.py keeps figure variants separate from current models.
  Paper small figure q10-o2->q6 differs from code q10-o1->q6. For the figure model,
  u5 winning with root{a,o2},u6 restores offline root{a,b,o2}; min decisive5/matching6.
  u5 closure graph has6 states7 edges;u6 has14 states19 edges. The six-step path
  q0-a-q1-a-q2-b-q4-o1-q8-u-q9-a-q10 explains the conservative boundary.
- Old component figure hasq2-o1->q0 and is offline losing; current user-corrected
  component q2-a->q0 is winning. Do not revert project examples to stale figures.
- rerun_paper_examples.py reruns both labels, small u5/u6, components, eight-copy
  legacy queries and certified attempts. Legacy50-query runs reset a physical
  state root; they are NOT partial-observation supervisor certificates. Certified
  u3/u7 and offline explicit enumeration hit5000-choice budgets; not infeasibility.
- Eight-copy corrected product has a fully enumerated feasible constant policy:
  disable all o1_i;6561 physical states52488 edges. Further composition of the
  certified component supervisor gives65536 reachable physical states,
 16777216 state/memory pairs,150994944 transitions,6561 memory configurations.
  Exact factored certificate+small1/2/3-copy exhaustive checks+100000 actual
  exported-controller steps; no global explicit BTS or global maximality claim.
- sync_paper_example_results.py updates ONLY active [paper].../main.tex case
  studies and *_rerun.pdf figure references. Old main/figures/PDF backed up under
  tmp/paper_examples_before_sync;main_original.tex and__paper archive untouched.
  Full Chinese u5/u6 explanation is in rerun report and运行结果.md; English is
  in active main.tex. pdflatex+BibTeX compile succeeded,7 pages, no undefined
  refs/controls/overfull boxes; latest figures visually checked. PDF at
  outputs/paper_examples_rerun/paper_examples_updated.pdf and active main.pdf.
- README now has module table/call responsibilities. CODE_REVIEW_GUIDE.md gives
  reading order, invariants, experiment scopes and legacy/current distinctions.
  Review bundle under outputs/code_review includes source/tests/manifests only,
  excluding environments/output datasets/paper PDFs.72 tests pass.

## Latest:61-case means, explicit decision agreement and negative savings

- Main table in运行结果.md now22 columns; added结果一致性（Online/Offline）,
  read directly from each saved online LL-BTS/offline BTS status.61/61 agree;
  all25 offline losing cases are also online losing. Inconclusive/budget failures
  are NOT treated as proven infeasibility; comparison_averages.py encodes this.
- Added averages immediately below node-count totals. Mean of61 per-model
  median total times:online0.138729508ms/offline0.279724590ms;50.404965% saving.
  Arithmetic mean of all671 raw repetitions:0.148592101/0.299061550ms;50.313873%.
  Mean separate Python peaks:21.411629/69.704150KiB;69.282131% saving.
- Main61-case table has14 negative time savings,0 negative memory/node savings.
  Random1000 details have291 negative time and170 negative peak-memory savings,
  0 negative node savings. Costs/complexity functions are not negative; the
  difference or savings fraction can be negative. All cases retained.
- Updated JSON/CSV/HTML and generators without rerunning any timing or changing
  model data.69 tests pass; averages_and_agreement_validation.json records audit.

## Latest: random experiment provenance and GitHub inspection

- Random-results heading now explicitly gives seed20261121,1000 inputs,5 runs,
  links to randomized_online_offline.py, certified_benchmark.random_plant,
  online/offline solver sources, and exact reproduction command. Source links
  are ../../ from expanded root, ../../../ from randomized_comparison/.
- Read-only git ls-remote verified origin https://github.com/trigger1996/des_common.git:
  default/only remote branch master, HEAD a80554581a373f9e73255626b44c9d24836912c6,
  same as local master (2026-09-11 updated). No fetch/pull/reset/commit/push.
- This does NOT mean working tree matches GitHub:6 tracked changes (including
  deleted parent .gitignore) and many untracked files. The new benchmark scripts,
  generator and certified/offline solver files are currently UNTRACKED, so the
  GitHub commit alone does not contain the local experimental implementation.
- Details saved in outputs/expanded_yin_benchmark/github_repository_check.json.

## Latest addition: graph counts, numerical cost models, random average experiment

- Project model/BTS inputs and existing timing measurements preserved. Main results
  table remains first, now21 columns: adds constructed LL-BTS/BTS D/O, totals,
  absolute node reduction and fraction. Counts validated against raw BTS JSON.
  61-case totals: BTS3346 (D330/O3016), LL-BTS665 (D175/O490), saved2681=80.1255%.
  Retained graph totals1238 vs393 are a separate metric, not construction counts.
- graph_size_metrics.py provides separate constructed/retained metrics and ratio
  of sums. compare_online_offline.py --refresh-report updates these without timing.
- complexity_memory_report.py generates COMPLEXITY_AND_MEMORY_CALCULATION.md/json
  with actual n,m,c,D,O,E,A,H,B,R,V. UR/NX checks B count expanded D times2^c;
  A is only saved choices and cannot replace B in online time bounds. Preprocessing
  longest-simple-path work can be factorial. Abstract work/reference-slot proxies
  are NOT actual seconds/bytes; hypothetical packed graph encoding is separate
  from tracemalloc new Python allocation peaks, which exclude common input/RSS.
- randomized_online_offline.py:1000 seeded partial DFAs,5 alternating fresh runs;
  predefined density0.70/0.45/0.30 strata, dense stratum fills outgoing edges.
  Online starts pre.horizon, retries only inconclusive; no offline-oracle u choice.
  All1000 timing+memory pairs completed, no timeouts. Primary target is existence
  of deadlock-free supervisor (1000/1000 decisions agree); root maximal modes agree991.
  Mean total times on0.07246172ms/off0.52386246ms:86.1678% saving,7.2295x.
  Mean peaks on12369.088/off91473.492 bytes:86.4780% saving. Constructed nodes
  on2547/off47006:94.5815% saving.709 models faster online; all others retained.
  Bootstrap paired mean time-difference CI and all strata/raw inputs/samples are
  under outputs/expanded_yin_benchmark/randomized_comparison. Distribution-specific,
  not a universal complexity reduction or policy-equivalence claim.

## Latest correction: 20CDC2_fig_2b and top results table

- User corrected the previously deferred request: add 2-b->2 and 6-c->6;
  retain 2-c->6. Both additions applied and deterministic. DEFERRED is now empty;
  total explicitly amended models29. Recomputed case remains losing,
  decisive/matching u0, draft/selected u2. Active counts remain36 winning/25 losing.
- `运行结果.md` now starts with the online/offline summary table immediately after
  the title, before methodology. Added state count, observable Sigma_o and
  controllable Sigma_c columns. Generator preserves this ordering.
- compare_online_offline.py --only NAME remeasures one model and preserves other
  measurements while refreshing aggregate reports. DFA audit now records the
  resolved request; no current conflict remains.

## Latest: 2026-11-21 user review amendments (supersedes older benchmark counts)

- Active corpus: 58 literature variants + 3 structural = 61; 36 winning / 25 losing.
- `examples/review_amendments.py` applies table instructions to original builders;
  `build_yin_literature_examples(amended=False)` retains all 61 original transcriptions.
- Original per-model data/images saved as plant_original.json/png; user requests,
  removals and deferred conflict in outputs/expanded_yin_benchmark/review_modifications.json.
- Removed original duplicates: yin2016_fig_1b, 17TAC-Range_fig_2c, 24TACopa_fig_1b;
  archived under tmp/user_review_revision_20261121/removed_examples.
- Gprime correction: user explicitly changed requested loops at 6,6' from c1 to c2;
  applied and recalculated (winning,u=3). Only deferred conflict: 20CDC2_fig_2b
  requested 2-c->2 would clash with existing 2-c->6; user said leave conflicts unchanged.
- Two separate Markdown files remain: 系统事件属性与修改意见.md and 运行结果.md.
  Index includes request/disposition columns; results include numeric summary with
  decisive/matching/selected u, online/offline total times, peaks, differences and ratios.
- All closed_loop_system_offline.* are under example/offline/. Canonical online
  files are closed_loop_system_online.*; generic closed_loop.* were removed.
- Both literature products now under large_systems/. Use revised_large_products.py:
  shared component LL-BTS/controller synthesis + exact asynchronous composition proof,
  not an explicitly constructed global LL-BTS. Global minimal u is NOT measured.
- Modified 18TACrange_fig_3a has deadlock 10; old all-Qe/all-enable product certificate
  invalid. New verified policy avoids 10; 7-copy plant19,487,171 physical states,
  controlled physical closed loop10,000,000. 21Automatica source unchanged.
- Old 31-day/131-TiB figure remains a historical root-stage explicit per-pattern
  forecast ONLY for the 21Automatica product; full offline not run. No global
  offline solve was rerun for large systems. refresh_large_catalogue.py draws
  sources/templates and labels the two large indexed chains as NOT products.
- Full pre-revision review/root results and old large output folders are archived
  under tmp/user_review_revision_20261121. Avoid reusing old all-enable results
  for the revised 18TACrange model. Plant renderer now curves past unrelated nodes.

## 2026-11-21 review document renamed and results integrated

- User renamed `系统事件属性与修改意见.md` to
  `系统事件属性与运行结果与修改意见.md` in expanded_yin_benchmark. Legacy file
  no longer exists. Original full text backed up at
  tmp/review_results_rename_20261121/original_review.md.
- `benchmark_review_results.py` enriches the document with 64 per-model
  analyses: Qd/Qf/Qe/u, online/offline counts, selected controller behavior,
  exclusive root-pattern rejection categories, complete closed-loop results,
  actual time/memory differences, ratios and formulas. Adds global scope/
  complexity limits and two large-product actual synthesis/validation sections.
- The 31-day offline number is explicitly a root-stage forecast for the FIRST
  large product only, not full measured offline time; latest31.0/19.6us actual
  runs are distinguished from historical25.1us forecast experiment.
- Preserve all original user note blocks (64), plus two new large-product note
  blocks (66 total), AND any handwritten text outside generated RUN-* regions.
  Generation is atomic, checks for concurrent edits, and renames from legacy
  only once. Idempotent generated-section replacement is unit-tested.
- Active generator/README/gallery links use the new filename. Do not recreate
  the old Markdown or overwrite user feedback during subsequent model work.

## 2026-11-21 actual large-product online supervisors completed

- User asked to actually run 1–2 examples and allowed up to half an hour.
  `run_large_literature_supervisors.py` completed both selected products online:
  21AutomaticaOptimal_fig_2 x6 (11390625 states,109350000 transitions),
  18TACrange_fig_3a x7 (19487171 states,173612978 transitions).
- Both retain all original event partitions. All component states are live and
  reachable; exact compositional Qe covers the entire product. Exported one-state
  C0 supervisors always enable every event, yield S/G=G and are maximally
  permissive for deadlock-freeness. No fairness/payoff/nonblocking claim.
- Actual fresh run total medians including compositional preprocessing:
  31.0 us and19.6 us; peaks7192/6328 Python bytes, input/index/testing/export
  excluded. Historical forecast25.1us remains separate from actual_online_run.
- Per model:100000 actual closed-loop steps with EXPORTED Python supervisor,
  exact factored observation-estimate membership checks, exhaustive1/2/3-copy
  all-state/all-transition checks,1000 constructed target-tuple reaching words.
  All-state guarantee is the compositional proof, NOT random testing. Full
  million-state products remain exact factored descriptions, not unrolled graphs.
- Results in dedicated literature_product_<source>_<k>copy folders;
  large_literature_supervisors.html is the combined entry. Each has executable
  supervisor_online.py,actual_online_run.json,raw timing/trajectory samples,
  SYNTHESIS_AND_VALIDATION.md and SVG/PNG. Source hashes checked.
- Fixed product-state JSON restoration: tuple product states decode from nested
  lists; renamed decode_estimate to avoid local-variable shadowing.59 tests pass.

## 2026-11-21 absolute savings and >10^7-state literature product forecast

- Comparison rows now include absolute time/byte/node/edge savings, ms/KiB/MiB,
  speedup and explicit formulas. Subtract same-unit values first; savings divide
  by offline. Online total is median of per-run (pre+solve), not sum of medians.
  Large indexed reports also include full raw values and worked arithmetic.
- Selected actual source 21AutomaticaOptimal_fig_2 (15 reachable states, 24
  transitions, 5 controllable/4 observable of 15 events, all states live).
  Six asynchronous copies: 15^6=11390625 reachable states, 109350000 transitions,
  30 controllable/24 observable/90 total events, partitions unchanged. All-enable
  single-memory controller gives an exact factored safe closed loop equal to G.
- `literature_product_forecast.py` verifies source offline controller and local
  reachability/hidden-DAG depth. Compositional Qe=entire product, Qd=Qf=empty;
  hidden depth sum supplies u=12. Generic online solver now checks an already
  proved root Qe BEFORE building its local window. This is sound and avoids a
  pointless huge Post scan. Separate tests cover partial Qe and budget=1.
- Actual target-size root UR has 729 states and six NX successors (486 each).
  No controllable event is enabled anywhere in that root UR, so all 2^30 root
  patterns share UR/NX but still produce distinct explicit O(pattern) nodes.
  Root samples (384 calls) measure current traditional per-pattern UR/NX+local
  deadlock check; 101 online repetitions include compositional preprocessing.
- Offline root time and retained-memory extrapolations are ESTIMATES ONLY.
  Full offline was not run and likely exceeds RAM first. Not a universal lower
  runtime bound: closure caching, bitsets, symbolic patterns or compositional
  offline synthesis change the comparison. This all-live example showcases Qe
  certificates, not mixed-risk-system performance. Avoid reporting huge forecast
  speedup as an observed end-to-end speedup. Source descriptor, raw samples,
  forecast, LL-BTS and symbolic closed-loop artifacts under the dedicated
  literature_product_21AutomaticaOptimal_fig_2_6copy benchmark folder.

## 2026-11-21 independent offline BTS and measured comparison

- `des_core/offline_bts.py` independently builds the FULL known-system BTS by
  every control pattern's complete UR/NX, including unsafe branches, THEN count
  prunes it. No u/Qf/Qe shortcuts. solve_offline now delegates here. Same goal
  and root maximal patterns as online; no claimed reproduction of other goals.
- `compare_online_offline.py` covers all 64 models: conventional offline/bts.*,
  supervisor_offline.*, closed_loop_system_offline.*, online aliases and fresh
  alternating repeated timing + separate allocation peaks. Original ll_bts.*
  in offline/ were noncompliant and 187 files were deleted after replacement;
  removal hashes/path manifest recorded. Old baseline fields in result rows
  are replaced with current protocol. User-editable review MD untouched.
- Root report distinguishes measured savings from asymptotic complexity. Actual
  count-pruning implementation operates on A choice records and H successor
  incidences: O(D+A+H), not blindly logical merged-graph O(V+E). Python record
  duplication is included in tracemalloc, with A/H/membership counts reported.
- Two complete indexed large known systems: 279936-state finite chain and
  1679616-state chain ending in a 3-cycle. All observable, one uncontrollable
  event; exact integer singleton UR/NX, complete D/O arrays actually built and
  pruned. Common input arrays excluded; online includes full preprocessing.
  These are NEW synthetic systems, NOT case-1 product relabelings.
- Original 7/8-copy case-1 products preserve inherited partitions, with
  2^21/2^24 patterns. Actual traditional/online attempts have explicit budgets
  and stop incomplete; no savings/unsolvability claim. A constant supervisor
  disabling all o1_i was separately fully verified on all 3^k reachable states;
  not claimed a completed maximal BTS synthesis. Product symbolic Qd/Qf/Qe/u
  formulas match explicit 1/2/3-copy preprocessing. Lazy product state-space
  membership added; online budget raises, never returns a fake conclusion.
- Large reports/binary complete graph data under expanded_yin_benchmark/
  large_systems/. See LARGE_SYSTEM_COMPARISON.md for explicit limitations.
- 55 unit tests pass, including conventional-BTS unsafe branches, hidden
  livelocks, budget truncation, indexed-vs-general equivalence and product
  certificate formulas. Keep these correctness limits in any future reporting.

## 2026-11-21 structural examples and editable model review

- User requested an explicit Markdown review file. The benchmark directory's
  `系统事件属性与修改意见.md` now catalogs all 64 original models with Sigma,
  observable/hidden/controllable/uncontrollable events, graph links and per-model
  editable USER-NOTES blocks. `write_benchmark_review.py` regenerates metadata
  while preserving all text inside those blocks. Never overwrite user opinions.
- Added `examples/structural.py` and `structural_benchmark.py`: a 16-state finite
  chain (losing,u=2), a 15-state chain/cycle/two terminal tails (winning,u=8),
  an 11-state chain with nested outer/inner cycles (winning,u=8). Inner and outer
  cycles share q6; custom plant drawings lay out the inner cycle inside the outer.
- Synthetic models remain separate from 61 literature models. paper_results.json
  stays literature-only; structural_results.json holds the three new tests;
  model_results.json/model_summary.json combine 64 cases (30 winning,34 losing).
  Closed-loop exports now cover these 64 plus six project configurations.
- No one-state original plants exist in either Yin benchmark directory; no
  deletion was needed under user's conditional instruction. Do not delete
  larger plants just because their certified LL-BTS or selected closed loop
  contains one state. Audit in single_state_plant_audit.json.
- 50 tests pass, including exact topology and synthesis checks for the three
  structural additions. Reproduce: structural_benchmark.py, draw_closed_loops.py,
  write_benchmark_review.py, in that order after the literature benchmark.

## 2026-11-21 user corrections: BibTeX and closed-loop provenance

- Supersedes the preboxed-citation fix below: user explicitly removed
  yincitationbox, unusedmathbox/notusedmath, and the hand-written bibliography.
  Citations are now ordinary cite commands outside CJKsout arguments, with
  bibliographystyle{IEEEtran}/bibliography{ref_full}. Math content was unwrapped
  without changing formulas; grey block annotations remain. Full BibTeX build
  is 14 pages with no undefined commands/references/citations or overfull boxes.
- Copied the deadlock-free/consistent LL-BTS definition and its original label
  from the paper's main.tex into the draft, before Corollary 1, with a notation
  paragraph. Restored the Definition reference with a normal nonbreaking space.
- User requires each literature example's supervisor/closed-loop artifacts in
  its existing outputs/expanded_yin_benchmark/<example>/ directory. The runner
  now reads saved plant.json and retained ll_bts.json edges directly, restores
  the certified policy without re-synthesis, and writes supervisor.json,
  closed_loop.json, diagrams and source SHA256s there. A Qe terminal expands its
  certified enable-all continuation. Existing separate gallery is a mirror.

## 2026-11-21 Overleaf fix and physical closed-loop gallery

- Fixed Response/technical_implementation_draft.tex: preboxed the deleted-text
  citation before CJKsout processes it, added a self-contained bibliography,
  replaced a dangling external definition reference with its explicit consistency
  conditions, and changed algorithm float placement to !ht. Protected theorem
  formulas and annotation styles were preserved. Clean XeLaTeX build: 13 pages,
  no undefined commands/references/citations, overfull boxes or float warnings.
  Backup and validation in tmp/overleaf_fix_20261121; portable Overleaf ZIP in
  the Response directory; PDF beside the source was updated.
- `des_core/closed_loop.py` extracts one deterministic observation-feedback
  supervisor from a certified policy and expands the full reachable physical
  product (q, controller memory). Hidden events retain memory. Qe certificate
  terminals expand enable-all continuation. Every allowed event is included.
- `python -X utf8 draw_closed_loops.py` exports 61 literature models and six
  project configurations to outputs/closed_loop_systems/index.html and ZIP.
  34 winning cases have genuine closed-loop graphs; 33 losing cases have status
  cards and original graphs. JSON, PNG, SVG, DOT and controller-memory CSV provided.
- CRITICAL: all_examples() partial-observation wrappers put an OBSERVER in dfa.
  For physical closed-loop synthesis use original_dfa when present. Using the
  observer as the plant drops hidden control actions and can falsely lose case 2.
  Current six project cases are all winning. Two names can share a physical
  configuration; keep legacy names rather than claiming all 67 are unique DFAs.
- Total 46 tests passed, including hidden-memory preservation, ambiguous
  observation outcomes, Qe expansion, disabling a deadlock branch and losing cases.

## 2026-11-21 expanded Yin corpus

- `examples/yin_literature.py` now returns 61 models (original 34 plus 27 in
  `examples/yin_extended.py`), from 22 source papers. Do not describe these as
  reproductions of the sources' opacity/attack/timing/marked-state objectives.
- All 222 entries on the current author publication page were inventoried;
  105 DES-topic PDF URLs were downloaded and text-screened. This is not a claim
  of exhaustive full-text visual review. `__ref/yin2016/expanded_inventory.json`
  records hashes, captions and provenance; 25LCSSepis's broken author link was
  recovered from coauthor Yiding Ji's university site, with both URLs recorded.
- `python -X utf8 expanded_yin_benchmark.py` exports to
  `outputs/expanded_yin_benchmark/`; `--no-plots` skips only PNG rendering.
  Scans every u=0..|Q|-1; selected_u must meet draft_u AND match complete offline
  root maximal patterns. Distinguish minimal_decisive_u from minimal_matching_u.
- 61 models: 28 winning, 33 losing; selected_u=0..5. All selected and full-window
  root maximal patterns match the offline baseline; all 43 unit tests passed.
- New useful nontrivial winning examples: 20CDC2 Fig.1a u=1 (D=3,O=6),
  23IFAC-attack Fig.2b u=3 (D=7,O=34). These are constructed node counts before
  pruning, not retained-policy counts. JSON includes retained flags/policy_edges.
- Preserve terminal states without invented loops. 16SEI uses a centralized
  pooled observation adaptation; four verification-source models introduce an
  explicitly documented all-controllable test partition. Other event partitions
  are inherited. eps in 17Mealy is an explicit hidden output-symbol event.
- Certified Qe terminals may reduce a safe model's LL-BTS to one D node; each
  model additionally exports complete offline BTS JSON/DOT without certificates.
  Large offline BTSs have no raster image; smaller ones also have PNGs.
- Prior 34-model/600-random-sample outputs were preserved. The existing
  certified_benchmark runner now imports the expanded 61-model corpus too.

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

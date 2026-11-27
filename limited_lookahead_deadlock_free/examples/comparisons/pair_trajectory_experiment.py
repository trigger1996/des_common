"""Per-observation and cumulative execution costs on identical controlled traces.

Full BTS is built ONCE, then its stored mode/NX table is reused. Online
structural analysis is also performed once. No repeated full construction is
charged to the baseline. Plots and validation are outside solve clocks.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
import json
from pathlib import Path
import random
from time import perf_counter

from examples.comparisons.compare_online_offline import load_plant
from des_core.automata import DFA
from des_core.certified_lookahead import Limited_Lookahead_Controller, preprocess, validate_policy
from des_core.offline_bts import construct_offline_bts
from des_core.resource_monitor import process_snapshot, interval_usage, environment_record
from examples.paper.paper_example_models import paper_small_figure


def run_case(name, plant, index, cap):
    before = process_snapshot()
    started = perf_counter()
    full = construct_offline_bts(plant)
    lookup = {x: {c.pattern: c for c in choices} for x, choices in full.policy.items()}
    full_seconds = perf_counter() - started
    full_resources = interval_usage(before, process_snapshot())
    before = process_snapshot()
    started = perf_counter()
    pre = preprocess(plant)
    analysis_seconds = perf_counter() - started
    analysis_resources = interval_usage(before, process_snapshot())
    controller = Limited_Lookahead_Controller(pre, minimum_horizon=True)
    rng = random.Random(20261121 + index)
    physical = plant.initial
    iterations = []
    online_total = analysis_seconds
    offline_total = full_seconds
    stop_reason = 'observation iteration cap'

    for k in range(cap):
        estimate = controller.estimate

        if estimate <= pre.Q_e:
            stop_reason = 'entered Q_e; enable all events and stop further construction'

            break

        before = process_snapshot()
        started = perf_counter()
        proof, fresh, fallback = controller.solve()
        pattern = max(proof.maximal_patterns, key=lambda p: (len(p), tuple(sorted(p)))) if proof.status == 'winning' else None
        elapsed = perf_counter() - started
        online_total += elapsed
        usage = interval_usage(before, process_snapshot())
        row = dict(k=k, estimate=sorted(estimate), physical_state_for_logging_only=physical,
                   status=proof.status, u=controller.horizon, online_seconds=elapsed,
                   fresh_construction_seconds=fresh.seconds, reused_previous_continuation=fallback,
                   online_cumulative_seconds=online_total, online_resources=usage,
                   D=fresh.decision_count, O=fresh.observation_count,
                   patterns_tested=fresh.patterns_tested, horizon_trials=fresh.horizon_trials)

        if proof.status != 'winning':
            assert full.status == proof.status == 'losing'
            stop_reason = 'proved losing; no execution'
            row['offline_cumulative_seconds'] = offline_total
            iterations.append(row)

            break

        validate_policy(pre, proof)
        started = perf_counter()
        full_choice = lookup[estimate][pattern]
        offline_lookup_seconds = perf_counter() - started
        offline_total += offline_lookup_seconds
        row.update(gamma_c=sorted(pattern), offline_lookup_seconds=offline_lookup_seconds,
                   offline_cumulative_seconds=offline_total)
        gamma = pattern | plant.uncontrollable
        hidden_seen = {physical}
        execution = []

        while True:
            enabled = [(e, target) for e, target in plant.enabled(physical) if e in gamma]
            assert enabled, ('deadlock in sampled controlled trace', name, physical)
            event, target = rng.choice(enabled)
            execution.append([physical, event, target])
            physical = target

            if event in plant.observable:
                started = perf_counter()
                expected = dict(full_choice.successors)[event]
                offline_update_seconds = perf_counter() - started
                offline_total += offline_update_seconds
                started = perf_counter()
                actual = controller.observe(pattern, event)
                online_update_seconds = perf_counter() - started
                online_total += online_update_seconds
                assert actual == expected and physical in actual
                row.update(observation=event, next_estimate=sorted(actual),
                           offline_update_seconds=offline_update_seconds,
                           online_update_seconds=online_update_seconds)

                break

            if physical in hidden_seen:
                stop_reason = 'chosen hidden cycle can repeat without another observation'
                row['hidden_cycle_continuation'] = True

                break

            hidden_seen.add(physical)

        row['execution'] = execution
        row['online_cumulative_seconds'] = online_total
        row['offline_cumulative_seconds'] = offline_total
        iterations.append(row)

        if row.get('hidden_cycle_continuation'):
            break

    return dict(name=name, full_initial_seconds=full_seconds, full_initial_resources=full_resources,
                structural_analysis_seconds=analysis_seconds, analysis_resources=analysis_resources,
                iterations=iterations, actual_constructions=len(iterations), cap=cap, stop_reason=stop_reason,
                online_total_seconds=online_total, offline_total_seconds=offline_total,
                seed=20261121 + index, offline_built_once=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iterations', type=int, default=50)
    args = parser.parse_args()
    base = Path('outputs/expanded_yin_benchmark')
    cases = [(r['name'], load_plant(base / r['name']))
             for r in json.loads((base / 'model_results.json').read_text(encoding='utf-8'))]

    for item in json.loads((base / 'randomized_comparison/plants.json').read_text(encoding='utf-8')):
        plant = DFA(frozenset(item['states']), item['initial'], frozenset(item['events']),
                    frozenset(item['controllable']), frozenset(item['observable']),
                    {(q, e): target for q, e, target in item['transitions']})
        cases.append(('random_' + str(item['index']), plant))

    cases.append(('paper_fig1_r1', paper_small_figure().dfa))
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []

    for index, (name, plant) in enumerate(cases):
        row = run_case(name, plant, index, args.iterations)
        (args.output / (name + '.json')).write_text(json.dumps(row, indent=2), encoding='utf-8')
        rows.append({k: v for k, v in row.items() if k != 'iterations'})

    summary = dict(models=len(rows), results=rows, environment=environment_record(),
        scope='Same LL-controlled trace for both implementations. Full construction is charged once, '
              'then only stored-mode and stored-NX lookups are charged. Online analysis is charged once, '
              'followed by actual observation-triggered reconstructions. A chosen hidden cycle is '
              'extended indefinitely as an allowed continuation; it does not mean all runs stop observing. '
              'The iteration cap is an experimental truncation, not a safety stopping rule.')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Trajectory profiles complete:', len(rows), 'models', flush=True)


if __name__ == '__main__':
    main()

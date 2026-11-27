"""Independent CPU/RAM batch profiles for the same 61 + 1000 saved inputs."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
import gc
import json
from pathlib import Path

from examples.comparisons.compare_online_offline import load_plant
from des_core.automata import DFA
from des_core.certified_lookahead import preprocess, solve_minimum_lookahead
from des_core.offline_bts import construct_offline_bts
from des_core.resource_monitor import process_snapshot, interval_usage, environment_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=('full', 'll'), required=True)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = Path('outputs/expanded_yin_benchmark')
    catalog = json.loads((base / 'model_results.json').read_text(encoding='utf-8'))
    plants = [(r['name'], load_plant(base / r['name'])) for r in catalog]

    for r in json.loads((base / 'randomized_comparison/plants.json').read_text(encoding='utf-8')):
        plant = DFA(frozenset(r['states']), r['initial'], frozenset(r['events']),
                    frozenset(r['controllable']), frozenset(r['observable']),
                    {(q, e): t for q, e, t in r['transitions']})
        plants.append(('random_' + str(r['index']), plant))

    for _, plant in plants:
        for q in plant.states:
            plant.enabled(q)

    gc.collect()
    before = process_snapshot()
    rows = []

    for repeat in range(args.repetitions):
        for name, plant in plants:
            if args.method == 'll':
                result = solve_minimum_lookahead(preprocess(plant))
            else:
                result = construct_offline_bts(plant)

            patterns = result.maximal_patterns
            rows.append(dict(name=name, repetition=repeat, status=result.status,
                             D=result.decision_count, O=result.observation_count,
                             patterns_tested=result.patterns_tested, maximal_patterns=len(patterns)))
            del result

    stats = interval_usage(before, process_snapshot())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(method=args.method, models=len(plants),
        repetitions=args.repetitions, solves=len(rows), statistics=stats,
        scope='Independent process per method. Common inputs and transition indexes loaded before '
              'the batch clock. No graph rendering or closed-loop validation inside the batch. '
              'OS peak working set is the process high-water mark including the common inputs.',
        environment=environment_record(), results=rows), indent=2), encoding='utf-8')
    print(args.method, 'batch', len(rows), 'solves;', stats, flush=True)


if __name__ == '__main__':
    main()

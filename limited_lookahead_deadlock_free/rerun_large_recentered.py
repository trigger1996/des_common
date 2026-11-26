"""Reproduce all completed product/large-scale rows with recentered windows.

python -X utf8 rerun_large_recentered.py --output outputs/recentered_large
No time or pattern budget; child processes use the requested memory guard.
"""

import argparse
from datetime import datetime
import gc
import json
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter

from des_core.asynchronous_product import ImplicitProductDFA
from des_core.offline_bts import construct_offline_bts
from early_stop_products import component, full_counts


def full_products(output, repetitions):
    for kind, n, copies in [('E', 10, 4), ('H', 100, 2)]:
        samples = []

        for _ in range(repetitions):
            gc.collect()
            started = perf_counter()
            plant = ImplicitProductDFA(component(kind, n), copies)
            result = construct_offline_bts(plant)
            result.maximal_patterns
            samples.append(perf_counter() - started)
            expected = full_counts(n, copies)
            assert result.status == 'winning'
            assert (result.decision_count, result.observation_count) == (expected['D'], expected['O'])
            del result, plant

        record = dict(case=kind + str(copies), complete=True, status='winning',
            D=expected['D'], O=expected['O'], samples_seconds=samples,
            mean_seconds=statistics.mean(samples), repetitions=repetitions,
            timing='Fresh component/product input plus native traditional full BTS and root maximal-pattern filtering.')
        (output / f'{kind}{copies}_full.json').write_text(json.dumps(record, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-memory-gib', type=float, default=8.)
    parser.add_argument('--repetitions', type=int, default=5)
    args = parser.parse_args()
    args.output = (args.output or Path('outputs/revision_materials') /
                   ('recentered_large_' + datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    project = Path(__file__).resolve().parent

    for kind, copies in [('E', 4), ('H', 2)]:
        subprocess.run([sys.executable, '-X', 'utf8', str(project / 'early_stop_products.py'),
            '--case', kind, '--copies', str(copies), '--repetitions', str(args.repetitions),
            '--max-memory-gib', str(args.max_memory_gib), '--output', str(args.output / kind)],
            cwd=project, check=True)

    full_products(args.output, args.repetitions)

    for family, options in [('products', ['--copies', '4']), ('chain', [])]:
        subprocess.run([sys.executable, '-X', 'utf8', str(project / 'large_scale_overall.py'),
            '--run', '--cases', family, *options, '--methods', 'full', 'll',
            '--max-memory-gib', str(args.max_memory_gib), '--output', str(args.output / family)],
            cwd=project, check=True)


if __name__ == '__main__':
    main()

"""Independent long CPU/RAM batches for the 45 common-input comparisons.

python -X utf8 three_method_resource_batches.py --minimum-seconds 2
This adds resource evidence without overwriting the five-repeat root timings.
No per-iteration metric list is retained inside the timed loop, so the RAM
peak does not grow simply because a faster method completes more repeats.
"""

import argparse
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from des_core.resource_monitor import environment_record, process_snapshot, interval_usage
from three_method_comparison import (ROOT, DEFAULT, METHODS, LABELS, components_for,
                                     calculate, input_hash, dump)


def run_batch(case, method, horizon, minimum_seconds):
    if minimum_seconds <= 0:
        raise ValueError('minimum_seconds must be positive')

    components = components_for(case)

    for plant, _ in components:
        for q in plant.states:
            plant.enabled(q)

    reference = calculate(method, components, horizon)
    fingerprint = (reference['root_status'], reference['constructed_states'],
                   reference['constructed_transitions'], reference['root_gamma_c'])
    del reference
    gc.collect()
    before = process_snapshot()
    started = perf_counter()
    count = 0
    total_solve_seconds = 0.0
    minimum = float('inf')
    maximum = 0.0

    while perf_counter() - started < minimum_seconds:
        metrics = calculate(method, components, horizon)
        assert (metrics['root_status'], metrics['constructed_states'],
                metrics['constructed_transitions'], metrics['root_gamma_c']) == fingerprint
        seconds = metrics['seconds']
        total_solve_seconds += seconds
        minimum = min(minimum, seconds)
        maximum = max(maximum, seconds)
        count += 1
        del metrics

    statistics = interval_usage(before, process_snapshot())

    return dict(case=case, method=LABELS[method], method_key=method, horizon=horizon,
                input_sha256=input_hash(components), minimum_seconds=minimum_seconds,
                solves=count, solve_seconds_sum=total_solve_seconds,
                mean_solve_seconds=total_solve_seconds / count,
                minimum_solve_seconds=minimum, maximum_solve_seconds=maximum,
                root_status=fingerprint[0], constructed_states=fingerprint[1],
                statistics=statistics,
                scope='Independent fresh process for this method/case/horizon. One untimed warmup and input-index '
                      'preparation precede timing. Each repetition includes required root setup/composition and, for LL, '
                      'structural analysis. No graph output, validation, tracemalloc, or growing result list in timed loop. '
                      'CPU utilization is the process CPU/wall ratio over the long batch, not sampled instantaneous CPU load. '
                      'Process RAM/commit high-water marks include the interpreter, common input, warmup and root solves.')


def write_summary(output, rows):
    lines = ['# 三方法独立长批次 CPU/RAM', '',
             '每种方法、例子、N 使用独立新进程；先完成一次不计时预热，再重复根求解至少2秒。',
             '每次重复均包含方法所需的组合/窗口构建；本文方法包含结构分析。',
             '循环内只累计标量，不保存不断增长的测量列表；无绘图、验证或tracemalloc。',
             'CPU百分比是进程CPU时间/批次wall时间，Machine再除以逻辑处理器数；不是瞬时采样曲线。',
             'RAM/Commit峰值是进程高水位，包含解释器、输入、预热和根求解，与Python分配峰值不同。', '',
             '| 例子 | N | 方法 | 重复数 | Wall/s | CPU/s | 单核/% | 全机/% | RAM/MiB | Commit/MiB |',
             '| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']

    for row in rows:
        stats = row['statistics']
        lines.append(f"| {row['case']} | {row['horizon']} | {row['method']} | {row['solves']} | "
                     f"{stats['wall_seconds']:.3f} | {stats['cpu_seconds']:.3f} | "
                     f"{stats['cpu_percent_one_core']:.2f} | {stats['cpu_percent_machine']:.2f} | "
                     f"{stats['peak_working_set_bytes'] / 2**20:.3f} | {stats['peak_commit_bytes'] / 2**20:.3f} |")

    lines += ['', '短批次原始CPU读数仍保留，本表为新增长批次，不能替换或拼接为原五次时间均值。',
              '所有数据见 resource_batches/*.json；其余闭环结果和输入在上级 three_method_comparison 目录。']
    (output / 'CPU_RAM长批次结果.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT / 'resource_batches')
    parser.add_argument('--minimum-seconds', type=float, default=2.0)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--case', help=argparse.SUPPRESS)
    parser.add_argument('--method', choices=METHODS, help=argparse.SUPPRESS)
    parser.add_argument('--horizon', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    if args.worker:
        row = run_batch(args.case, args.method, args.horizon, args.minimum_seconds)
        dump(args.output / f'{args.case}_N{args.horizon}_{args.method}.json', row)
        print(args.case, args.horizon, LABELS[args.method], row['solves'], 'solves;',
              f"CPU={row['statistics']['cpu_seconds']:.3f}s", flush=True)

        return

    source = DEFAULT / 'summary.json'
    comparisons = json.loads(source.read_text(encoding='utf-8'))
    names = [Path(__file__), ROOT / 'three_method_comparison.py', ROOT / 'des_core/resource_monitor.py',
             ROOT / 'des_core/classic_llp_1992.py', ROOT / 'des_core/warehouse_2018.py',
             ROOT / 'des_core/certified_lookahead.py']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in names}
    dump(args.output / 'manifest.json', dict(environment=environment_record(), minimum_seconds=args.minimum_seconds,
        source_sha256=hashes, reference_summary=str(source), reference_summary_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        configurations=len(comparisons), one_process_per_configuration=True))
    rows = []

    for comparison in comparisons:
        command = [sys.executable, '-X', 'utf8', str(Path(__file__)), '--worker',
                   '--case', comparison['case'], '--method', comparison['method_key'],
                   '--horizon', str(comparison['horizon']), '--minimum-seconds', str(args.minimum_seconds),
                   '--output', str(args.output)]
        subprocess.run(command, cwd=ROOT, check=True)
        row = json.loads((args.output / f"{comparison['case']}_N{comparison['horizon']}_{comparison['method_key']}.json").read_text(encoding='utf-8'))
        assert row['input_sha256'] == comparison['input_sha256']
        assert row['constructed_states'] == comparison['constructed_states']
        rows.append(row)
        dump(args.output / 'summary.json', rows)
        write_summary(args.output, rows)

    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    print('Completed independent CPU/RAM profiles:', len(rows), flush=True)


if __name__ == '__main__':
    main()

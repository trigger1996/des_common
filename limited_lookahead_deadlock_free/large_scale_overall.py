"""Resource estimates and global large-scale runs without fixed solve budgets.

Estimate only (default): python -X utf8 large_scale_overall.py
Run feasible comparisons: python -X utf8 large_scale_overall.py --run
Run LL alone: python -X utf8 large_scale_overall.py --run --cases products --copies 6 --methods ll

There is no default wall-clock, control-pattern, or lookahead-window limit.
--max-memory-gib is an optional process working-set guard. Ctrl+C saves progress.
New runs always use a separate timestamped output directory.
"""

import argparse
from collections import defaultdict
import ctypes
from ctypes import wintypes
from datetime import datetime
from itertools import product as tuples
import json
import os
from pathlib import Path
import platform
import random
import signal
import subprocess
import sys
from time import perf_counter, sleep

import des_core.certified_lookahead as online_core
import des_core.offline_bts as offline_core
from des_core.closed_loop import build_closed_loop
from des_core.asynchronous_product import ImplicitProductDFA
from global_large_case_studies import build_global_dfa
from hard_product_case_studies import product_analysis


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def memory_status():
    class Status(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in
            ('total', 'available', 'page', 'available_page', 'virtual', 'available_virtual', 'extended')]

    state = Status()
    state.length = ctypes.sizeof(state)

    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        raise ctypes.WinError()

    return dict(total_bytes=state.total, available_bytes=state.available)


def working_set(handle, peak=False):
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in
            ('peak', 'working', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged',
             'pagefile', 'peak_pagefile', 'private')]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    query.restype = wintypes.BOOL

    if not query(wintypes.HANDLE(int(handle)), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()

    return counters.peak if peak else counters.working


def ll_counts(copies):
    """Exact recentered LL counts for the P family, copies >= 2."""

    if copies < 2:
        return {}

    k = copies
    nonsafe = 9 ** k
    decisions = nonsafe - 1 + k * 9 ** (k - 1)
    expandable = nonsafe - 1 - 6 * k
    modes = 2 ** k
    observations = modes * expandable
    floor = (sys.getsizeof(online_core.Choice(frozenset(), frozenset(), ()))
             + 2 * sys.getsizeof(frozenset()) + sys.getsizeof(()))
    successor_pairs = modes * (k * nonsafe - 6 * k)
    successor_floor = (sys.getsizeof((None, None)) + sys.getsizeof(frozenset())
                       + sys.getsizeof((None,)) - sys.getsizeof(()))

    return dict(LL_D_exact=decisions, LL_O_exact=observations,
                LL_nodes_exact=decisions + observations,
                LL_minimum_payload_bytes=observations * floor + successor_pairs * successor_floor,
                LL_successor_pairs_exact=successor_pairs, bar_u=0,
                LL_selected_horizon_exact=k + 1,
                LL_final_pattern_checks_exact=expandable * modes,
                LL_all_horizon_pattern_checks_exact=expandable * modes + k * modes,
                LL_memory_scope='Mandatory Choice, pattern, closure, successor tuple and every '
                    'nonempty NX pair/frozenset/reference; excludes state tuples, transitions, maps and pruning.',
                window_semantics='Each complete decision estimate recenters its own horizon.')


def estimate_product(copies, samples=256):
    """Uniform global estimate/mode samples, rather than root-only sampling.

    Each local estimate factor is A={q0,q1}, B={q1,q2}, C={q2}, or one of
    the seven failure-chain singleton states. Every factor tuple other than
    all-A is reachable after an observation; the separate initial estimate
    replaces all-A. Closures of these estimates are distinct. Thus Full has
    exactly 10^k decision and 20^k observation nodes in this family.
    """

    plant = product_analysis(copies).plant
    local = [('q0', 'q1'), ('q1', 'q2'), ('q2',)] + [(f'q{i}',) for i in range(3, 10)]
    controls = sorted(plant.controllable)
    rng = random.Random(20261123 + copies)
    times = []
    choices = []

    for _ in range(samples):
        indices = [rng.randrange(10) for _ in range(copies)]

        while not any(indices):
            indices = [rng.randrange(10) for _ in range(copies)]

        estimate = frozenset(tuples(*(local[i] for i in indices)))
        pattern = frozenset(e for e in controls if rng.getrandbits(1))
        started = perf_counter()
        choice = offline_core.traditional_ur_nx(plant, estimate, pattern)
        enabled = pattern | plant.uncontrollable
        all(any(e in enabled for e, _ in plant.enabled(q)) for q in choice.closure)
        times.append(perf_counter() - started)
        choices.append(choice)

    # A strict per-pattern lower bound from separately allocated objects.
    # Exclude the one all-dead decision, whose successor tuple is empty.
    floor = (min(sys.getsizeof(c) for c in choices) + sys.getsizeof(frozenset({'x'})) * 3
             + sys.getsizeof((0,)) + sys.getsizeof((0, 0)))
    decisions = 10 ** copies
    patterns = 2 ** copies
    observation_nodes = decisions * patterns
    minimum = (decisions - 1) * patterns * floor
    coefficients = [1]

    for _ in range(copies):
        next_coefficients = [0] * (len(coefficients) + 7)

        for i, coefficient in enumerate(coefficients):
            for cost, multiplicity in enumerate((1, 2, 2, 1, 1, 1, 1, 1)):
                next_coefficients[i + cost] += coefficient * multiplicity

        coefficients = next_coefficients

    return dict(copies=copies, states=decisions, full_D_exact=decisions,
                full_O_exact=observation_nodes, full_nodes_exact=decisions + observation_nodes,
                full_pattern_checks_exact=observation_nodes,
                full_minimum_bytes=minimum, minimum_bytes_per_nondead_pattern=floor,
                minimum_scope='Choice object + distinct pattern/closure/successor frozensets + '
                    'nonempty successor tuple and one successor pair; excludes most graph storage.',
                sampling_seed=20261123 + copies, samples=samples,
                sampled_mean_ur_nx_seconds=sum(times) / len(times),
                extrapolated_ur_nx_liveness_seconds=observation_nodes * sum(times) / len(times),
                timing_scope='Uniform reachable global estimate-factor/mode samples. '
                    'UR/NX and liveness only; not a measured or predicted complete solve time.',
                safe_policy_window_horizon=copies + 1,
                safe_policy_window_states_exact=sum(coefficients[:copies + 2]),
                **ll_counts(copies))


def validate_full_counts():
    rows = []

    for copies in (1, 2, 3):
        result = offline_core.construct_offline_bts(product_analysis(copies).plant)
        assert result.decision_count == 10 ** copies
        assert result.observation_count == 20 ** copies
        rows.append(dict(copies=copies, D=result.decision_count, O=result.observation_count))

    for copies in (2, 3, 4):
        result = online_core.solve_limited_lookahead(product_analysis(copies), horizon=copies + 1)
        expected = ll_counts(copies)
        assert result.status == 'winning'
        assert result.decision_count == expected['LL_D_exact']
        assert result.observation_count == expected['LL_O_exact']
        assert sum(len(c.successors) for cs in result.constructed_choices.values() for c in cs) == expected['LL_successor_pairs_exact']
        rows.append(dict(copies=copies, method='LL', D=result.decision_count, O=result.observation_count))

    return rows


def run_worker(args):
    path = args.output / f'{args.family}_{args.copies}_{args.method}.json'
    started = perf_counter()
    record = dict(family=args.family, copies=args.copies, method=args.method,
                  complete=False, patterns_started=0, patterns_completed=0,
                  decision_estimates_started=0, trials=[], phase='initial structural analysis')
    record['baseline_working_set_bytes'] = working_set(-1)
    last_write = 0.
    last_estimate = None

    def save(force=False):
        nonlocal last_write
        now = perf_counter()

        if force or now - last_write >= 5.:
            record['elapsed_seconds'] = now - started
            dump(path, record)
            last_write = now

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, interrupt)

    save(True)

    try:
        if args.family == 'products':
            if args.method == 'll':
                pre = product_analysis(args.copies)
            else:
                pre = None
                plant = ImplicitProductDFA(build_global_dfa(10, 3), args.copies)
        else:
            plant = build_global_dfa(args.chain_states, args.chain_spine)
            plant.enabled(plant.initial)
            pre = None

            if args.method == 'll':
                pre = online_core.preprocess(plant)

        plant = pre.plant if pre is not None else plant
        record['states'] = len(plant.states)
        record['input_setup_seconds'] = perf_counter() - started
        record['structural_seconds'] = pre.seconds if pre is not None else 0.
        record['bar_u'] = pre.lookahead_lower_bound if pre is not None else None
        original = (offline_core.traditional_ur_nx if args.method == 'full'
                    else online_core.limited_choice)

        def tracked(plant, estimate, pattern, *rest):
            nonlocal last_estimate
            record['patterns_started'] += 1

            if estimate is not last_estimate:
                record['decision_estimates_started'] += 1
                last_estimate = estimate

            save()
            result = original(plant, estimate, pattern, *rest)
            record['patterns_completed'] += 1

            return result

        if args.method == 'full':
            offline_core.traditional_ur_nx = tracked
            record['phase'] = 'full BTS construction and pruning'
            save(True)
            result = offline_core.construct_offline_bts(plant)
        else:
            online_core.limited_choice = tracked

            horizons = ([args.copies + 1] if args.final_window_only and args.family == 'products'
                        else range(max(1, pre.u_f), len(plant.states)))

            for u in horizons:
                record.update(phase='LL window/construction/pruning', current_u=u)
                save(True)
                result = online_core.solve_limited_lookahead(pre, horizon=u)
                record['trials'].append(dict(u=u, status=result.status,
                    window=len(result.window), D=result.decision_count, O=result.observation_count))
                save(True)

                if result.status != 'inconclusive':
                    break

        record.update(complete=True, status=result.status, u=result.horizon,
                      D=result.decision_count, O=result.observation_count,
                      nodes=result.decision_count + result.observation_count,
                      final_construction_seconds=result.seconds,
                      solve_seconds=perf_counter() - started, phase='validating completed policy')
        record['solve_peak_working_set_bytes'] = working_set(-1, peak=True)
        save(True)

        if result.status == 'winning' and args.method == 'll':
            record['policy_validation'] = online_core.validate_policy(pre, result)

            if args.export_closed_loop:
                graph = build_closed_loop(pre, result)
                dump(path.with_name(path.stem + '_closed_loop.json'), graph)
                record['closed_loop_states'] = len(graph['nodes'])

        record['phase'] = 'finished'
        save(True)
    except KeyboardInterrupt:
        record.update(status='interrupted', phase='interrupted; counts are partial')
        save(True)
    except MemoryError:
        record.update(status='memory exhausted', phase='incomplete')
        save(True)

        raise


def launch(args, family, copies, method):
    command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), '--worker',
               '--family', family, '--copies', str(copies), '--method', method,
               '--output', str(args.output), '--chain-states', str(args.chain_states),
               '--chain-spine', str(args.chain_spine)]

    if args.final_window_only:
        command.append('--final-window-only')

    if args.export_closed_loop:
        command.append('--export-closed-loop')

    child = subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    path = args.output / f'{family}_{copies}_{method}.json'
    next_update = perf_counter()
    stopped_for_memory = False

    try:
        while child.poll() is None:
            try:
                rss = working_set(child._handle)
            except OSError:
                if child.poll() is not None:
                    break

                raise

            if args.max_memory_gib is not None and rss > args.max_memory_gib * 2 ** 30:
                stopped_for_memory = True
                child.send_signal(signal.CTRL_BREAK_EVENT)

                break

            if perf_counter() >= next_update:
                record = json.loads(path.read_text()) if path.exists() else {}
                print(f'{family} {copies} {method}: {rss / 2 ** 30:.2f} GiB, '
                      f'patterns={record.get("patterns_completed", 0)}, '
                      f'u={record.get("current_u")}, phase={record.get("phase", "starting")}', flush=True)
                next_update = perf_counter() + 30.

            sleep(1.)
    except KeyboardInterrupt:
        child.send_signal(signal.CTRL_BREAK_EVENT)
        child.wait()

        raise

    child.wait()
    record = json.loads(path.read_text())

    if stopped_for_memory:
        record['stop_reason'] = 'optional user-specified memory guard'
        dump(path, record)

    if child.returncode and not stopped_for_memory:
        raise RuntimeError(f'Worker exited with {child.returncode}; inspect {path}')

    print('Result:', path, record.get('status'), 'nodes=', record.get('nodes'), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Execute; otherwise only estimate resources.')
    parser.add_argument('--estimate-only', action='store_true')
    parser.add_argument('--cases', nargs='+', choices=('products', 'chain'), default=['products', 'chain'])
    parser.add_argument('--copies', nargs='+', type=int, default=[6, 7, 8])
    parser.add_argument('--methods', nargs='+', choices=('full', 'll'), default=['full', 'll'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-memory-gib', type=float, default=None)
    parser.add_argument('--force', action='store_true', help='Ignore the full-BTS memory feasibility check.')
    parser.add_argument('--final-window-only', action='store_true',
                        help='Calibrate products at their proved first successful horizon k+1, without scanning.')
    parser.add_argument('--export-closed-loop', action='store_true',
                        help='Additionally enumerate the selected supervisor closed loop after validation.')
    parser.add_argument('--chain-states', type=int, default=1_000_000)
    parser.add_argument('--chain-spine', type=int, default=128)
    parser.add_argument('--calibration', type=Path,
                        help='Completed smaller-product LL JSON for indicative runtime/RAM extrapolation.')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--family', choices=('products', 'chain'), help=argparse.SUPPRESS)
    parser.add_argument('--method', choices=('full', 'll'), help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.worker:
        args.copies = args.copies[0]
        run_worker(args)

        return

    args.output = (args.output or Path('outputs/revision_materials') /
                   ('large_scale_overall_' + datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    hardware = memory_status()
    estimates = [estimate_product(k) for k in args.copies] if 'products' in args.cases else []

    if args.calibration:
        calibration = json.loads(args.calibration.read_text())
        assert calibration['complete'] and calibration['method'] == 'll'
        base_k = calibration['copies']
        base = ll_counts(base_k)
        peak_delta = max(0, calibration['solve_peak_working_set_bytes']
                         - calibration['baseline_working_set_bytes'])

        for row in estimates:
            counts = row['LL_final_pattern_checks_exact'] / base['LL_final_pattern_checks_exact']
            payload = row['LL_minimum_payload_bytes'] / base['LL_minimum_payload_bytes']
            per_check_growth = payload / counts
            final_time = calibration['solve_seconds'] * counts * per_check_growth * row['copies'] / base_k
            total_time = final_time * row['LL_all_horizon_pattern_checks_exact'] / row['LL_final_pattern_checks_exact']
            peak = calibration['baseline_working_set_bytes'] + peak_delta * payload * row['copies'] / base_k
            row.update(LL_calibrated_final_window_seconds=final_time,
                       LL_calibrated_all_horizons_seconds=total_time,
                       LL_calibrated_peak_bytes=peak,
                       LL_indicative_seconds_range=[total_time * .5, total_time * 2.],
                       LL_indicative_peak_range_bytes=[peak * .75, peak * 1.5],
                       LL_calibration_source=str(args.calibration),
                       LL_calibration_scope='Indicative size/payload and coordinate-count scaling from '
                           'a smaller complete run; not a guaranteed bound or measured target result.')

    validations = validate_full_counts() if estimates else []
    record = dict(hardware=hardware, products=estimates, exact_full_count_checks=validations,
                  machine=dict(python=sys.version, platform=platform.platform(),
                               processor=platform.processor(), logical_cpus=os.cpu_count()),
                  runtime_limits=None, pattern_limits=None, window_limits=None,
                  optional_memory_guard_gib=args.max_memory_gib)
    dump(args.output / 'resource_estimates.json', record)
    print('RAM total/available GiB:', hardware['total_bytes'] / 2 ** 30,
          hardware['available_bytes'] / 2 ** 30, flush=True)

    for row in estimates:
        print(f'P{row["copies"]}: Full nodes={row["full_nodes_exact"]:,}, '
              f'strict minimum memory={row["full_minimum_bytes"] / 2 ** 30:.2f} GiB, '
              f'UR/NX-only forecast={row["extrapolated_ur_nx_liveness_seconds"]:.1f} s; '
              'not a total solve forecast', flush=True)
        print(f'    LL nodes={row.get("LL_nodes_exact", "not derived"):,}, '
              f'mandatory payload={row.get("LL_minimum_payload_bytes", 0) / 2 ** 30:.2f} GiB, '
              f'final/all-horizon checks={row.get("LL_final_pattern_checks_exact")}/'
              f'{row.get("LL_all_horizon_pattern_checks_exact")}', flush=True)

        if 'LL_calibrated_all_horizons_seconds' in row:
            print(f'    LL calibrated scan forecast={row["LL_calibrated_all_horizons_seconds"] / 60:.1f} min, '
                  f'peak={row["LL_calibrated_peak_bytes"] / 2 ** 30:.2f} GiB; '
                  'indicative extrapolation, not a measured target result', flush=True)

    print('Estimates:', args.output / 'resource_estimates.json', flush=True)

    if not args.run or args.estimate_only:
        return

    for row in estimates:
        for method in args.methods:
            minimum = row['full_minimum_bytes'] if method == 'full' else row.get('LL_minimum_payload_bytes', 0)

            allowance = min(hardware['available_bytes'], args.max_memory_gib * 2 ** 30) if args.max_memory_gib else hardware['available_bytes']

            if minimum > allowance and not args.force:
                print('Skipping P', row['copies'], method,
                      ': its mandatory stored payload exceeds available RAM or the memory guard.', flush=True)
                dump(args.output / f'products_{row["copies"]}_{method}.json', dict(
                     complete=False, status='not_run_memory_lower_bound', copies=row['copies'],
                     method=method, minimum_payload_bytes=minimum, allowance_bytes=allowance,
                     reason='Resource lower bound exceeds available RAM or configured memory guard.'))

                continue

            launch(args, 'products', row['copies'], method)

    if 'chain' in args.cases:
        for method in args.methods:
            launch(args, 'chain', 1, method)


if __name__ == '__main__':
    main()

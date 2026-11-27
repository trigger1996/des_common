"""Reproduce all current experiments after correcting decision-state identity.

python -X utf8 scripts/maintenance/rerun_all_pair_states.py
Each stage is sequential. Render/serialization stages are separate from the
timed solver batches. The status and resource profile of every stage are saved.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter, sleep
import zipfile

from des_core.resource_monitor import process_snapshot, interval_usage, environment_record


DEFAULT = Path('outputs/revision_materials/pair_states_final_20261123')


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def run_stage(name, command, root):
    profile_path = root / 'stage_profiles' / (name + '.json')

    if profile_path.exists() and json.loads(profile_path.read_text())['exit_code'] == 0:
        print('already complete:', name, flush=True)

        return

    log_path = root / 'logs' / (name + '.log')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = reported = perf_counter()
    samples = []
    dump(root / 'status.json', dict(stage=name, state='running', command=command))

    with log_path.open('w', encoding='utf-8') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)

        try:
            while child.poll() is None:
                try:
                    samples.append(process_snapshot(child._handle))
                except OSError:
                    pass

                if perf_counter() - reported >= 15:
                    reported = perf_counter()
                    print(name, 'running', round(reported - started), 's', flush=True)
                    dump(root / 'status.json', dict(stage=name, state='running',
                         elapsed_seconds=reported - started, log=str(log_path)))

                sleep(.2)
        except BaseException:
            child.terminate()
            child.wait()

            raise

        try:
            samples.append(process_snapshot(child._handle))
        except OSError:
            pass

    profile = dict(stage=name, command=command, exit_code=child.returncode,
                   elapsed_seconds=perf_counter() - started, samples=samples,
                   scope='Direct child process. Large solver children have separate '
                         'construction_resources in each case record.')

    if samples:
        profile['sampled_peak_working_set_bytes'] = max(s.get('working_set_bytes', 0) for s in samples)
        profile['sampled_peak_private_bytes'] = max(s.get('private_bytes', 0) for s in samples)
        profile['cpu_interval'] = interval_usage(samples[0], samples[-1])

    dump(profile_path, profile)
    print(name, 'finished', child.returncode, flush=True)

    if child.returncode:
        dump(root / 'status.json', dict(stage=name, state='failed', log=str(log_path)))

        raise subprocess.CalledProcessError(child.returncode, command)


def archive_inputs_and_old_reports(root):
    target = root / 'previous_reports.zip'

    if target.exists() or (root / 'input_manifest.json').exists():
        return

    base = Path('outputs/expanded_yin_benchmark')
    models = json.loads((base / 'model_results.json').read_text(encoding='utf-8'))
    files = set(base.glob('*.json')) | set(base.glob('*.md'))

    for row in models:
        folder = base / row['name']
        files.update(folder.glob('*.json'))
        files.update(folder.glob('ll_bts*'))
        files.update((folder / 'offline').glob('bts*'))

    files.update((base / 'randomized_comparison').glob('*.json'))

    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in files if p.is_file()):
            archive.write(path, str(path))

    plants = base / 'randomized_comparison/plants.json'
    dump(root / 'input_manifest.json', dict(
        random_input_sha256=hashlib.sha256(plants.read_bytes()).hexdigest(),
        reviewed_inputs={row['name']: hashlib.sha256((base / row['name'] / 'plant.json').read_bytes()).hexdigest()
                         for row in models},
        source_snapshot_time=datetime.now().isoformat()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    archive_inputs_and_old_reports(root)
    dump(root / 'environment.json', environment_record())
    python = [sys.executable, '-X', 'utf8']
    jobs = [
        ('corpus', python + ['examples/paper/manuscript_case_studies.py', '--part', 'corpus', '--output', str(root / 'corpus')]),
        ('large', python + ['examples/large_scale/nonzero_lookahead_cases.py', '--run', '--cases',
            'E4', 'H2', 'P4', 'E5', 'H3', 'P5', 'C', 'E4_zero', '--repetitions', '1',
            '--max-memory-gib', '20', '--output', str(root / 'large')]),
        ('cpu_full', python + ['examples/comparisons/pair_resource_batches.py', '--method', 'full', '--output', str(root / 'cpu/full.json')]),
        ('cpu_ll', python + ['examples/comparisons/pair_resource_batches.py', '--method', 'll', '--output', str(root / 'cpu/ll.json')]),
        ('reviewed_graphs', python + ['scripts/maintenance/refresh_recentered_benchmarks.py']),
        ('reviewed_measurements', python + ['examples/comparisons/compare_online_offline.py', '--repetitions', '11']),
        ('randomized_canonical', python + ['examples/comparisons/randomized_online_offline.py', '--samples', '1000',
            '--repetitions', '5', '--seed', '20261121']),
        ('ablations', python + ['-c', 'from pathlib import Path; import examples.paper.revision_experiments as m; '
            + 'm.OUT=Path(' + repr(str(root / 'ablations')) + '); m.main()']),
        ('threshold_sensitivity', python + ['examples/comparisons/compare_deadlock_target_bound.py']),
        ('fig1', python + ['examples/paper/rebuild_fig1_r1.py', '--output', str(root / 'fig1')]),
        ('small', python + ['examples/paper/manuscript_case_studies.py', '--part', 'small', '--output', str(root / 'paper_small')]),
        ('trajectories', python + ['examples/comparisons/pair_trajectory_experiment.py', '--output', str(root / 'trajectories')]),
    ]

    for name, command in jobs:
        run_stage(name, command, root)

    inputs = json.loads((root / 'input_manifest.json').read_text())
    plants = Path('outputs/expanded_yin_benchmark/randomized_comparison/plants.json')
    assert hashlib.sha256(plants.read_bytes()).hexdigest() == inputs['random_input_sha256']
    dump(root / 'status.json', dict(state='experiments_complete', stages=[name for name, _ in jobs],
                                   next='Verify results and refresh manuscripts, supplementary material and figures.'))
    print('All experimental stages completed.', flush=True)


if __name__ == '__main__':
    main()

"""Inventory or remove superseded outputs, preserving current case-study data.

python -X utf8 clean_non_case_outputs.py
python -X utf8 clean_non_case_outputs.py --apply
Only directories below this project's outputs directory can be removed.
The PowerShell removal step uses verified literal paths in this manifest.
"""

import argparse
import hashlib
import json
from pathlib import Path


KEEP_ROOT = {'case_studies', 'expanded_yin_benchmark', 'revision_materials'}
KEEP_REVISION = {'pair_states_final_20261123', 'fig1_r1_20261123'}


def inventory(path):
    files = [path] if path.is_file() else [item for item in path.rglob('*') if item.is_file()]

    return dict(path=str(path.resolve()), files=len(files), bytes=sum(item.stat().st_size for item in files))


def build_plan():
    root = Path(__file__).resolve().parent
    outputs = (root / 'outputs').resolve()
    targets = [path for path in outputs.iterdir() if path.name not in KEEP_ROOT]
    revision = outputs / 'revision_materials'
    targets.extend(path for path in revision.iterdir() if path.name not in KEEP_REVISION)
    final = revision / 'pair_states_final_20261123'
    targets.extend(path for path in final.glob('*.zip') if path.name != 'source_before_layout.zip')
    targets.extend(path for path in final.rglob('*_partial.json'))
    kept = {}

    for folder in [outputs / 'expanded_yin_benchmark', final]:
        for path in folder.rglob('*'):
            if path.is_file() and (path.name in ('plant.json', 'plants.json', 'input_manifest.json')
                                   or path.suffix == '.md'):
                kept[str(path.relative_to(outputs))] = hashlib.sha256(path.read_bytes()).hexdigest()

    for path in targets:
        resolved = path.resolve()
        assert resolved.is_relative_to(outputs) and resolved != outputs, path
        assert not path.is_symlink() and not path.is_junction(), path

    rows = [inventory(path) for path in targets]

    return dict(workspace=str(root), outputs=str(outputs), targets=rows,
                total_files=sum(row['files'] for row in rows), total_bytes=sum(row['bytes'] for row in rows),
                preserved_input_and_note_hashes=kept,
                retained=['outputs/case_studies/', 'outputs/expanded_yin_benchmark/',
                          'outputs/revision_materials/pair_states_final_20261123/',
                          'outputs/revision_materials/fig1_r1_20261123/'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    plan = build_plan()
    directory = Path('outputs/revision_materials/pair_states_final_20261123')
    destination = directory / ('cleanup_manifest.json' if args.apply and plan['targets'] else 'cleanup_preview.json')

    if args.apply and plan['targets'] and destination.exists():
        history = directory / 'cleanup_history'
        history.mkdir(exist_ok=True)
        prior = destination.read_bytes()
        (history / (hashlib.sha256(prior).hexdigest()[:16] + '.json')).write_bytes(prior)

    destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Superseded files:', plan['total_files'], 'GiB:', round(plan['total_bytes'] / 2**30, 3))

    if args.apply:
        if not plan['targets']:
            print('No superseded outputs remain; previous applied cleanup manifest preserved.')

            return

        import subprocess

        script = Path(__file__).resolve().parent / 'scripts/clean_non_case_outputs.ps1'
        subprocess.run(['powershell.exe', '-NoProfile', '-File', str(script),
                        '-Manifest', str(destination.resolve())], check=True)

        for name, digest in plan['preserved_input_and_note_hashes'].items():
            path = Path(plan['outputs']) / name
            assert path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest, name

        plan['applied'] = True
        plan['preserved_hashes_verified'] = True
        destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Removed superseded outputs; retained inputs and user notes verified unchanged.')
    else:
        print('Inventory only. Use --apply to remove the listed outputs.')


if __name__ == '__main__':
    main()

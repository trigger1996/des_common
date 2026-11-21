"""One-time migration of saved benchmark artifacts, with content checks."""
import hashlib
import json
from pathlib import Path
import re

root=Path('outputs/expanded_yin_benchmark').resolve()
manifest=[]
for source in sorted(root.rglob('closed_loop_system_offline.*')):
    if source.parent.name=='offline':
        continue
    destination=source.parent/'offline'/source.name
    assert source.resolve().is_relative_to(root)
    assert destination.resolve().is_relative_to(root)
    assert not destination.exists(),destination
    original=source.read_bytes()
    destination.parent.mkdir(exist_ok=True)
    source.rename(destination)
    assert destination.read_bytes()==original
    # These two fields are paths relative to the JSON itself.
    if destination.suffix=='.json':
        data=json.loads(original)
        changed=False
        if data.get('estimate_file')=='forecast.json':
            data['estimate_file']='../forecast.json';changed=True
        edges=data.get('edges')
        if isinstance(edges,dict) and edges.get('file')=='plant_successors_i32.bin':
            edges['file']='../plant_successors_i32.bin';changed=True
        if changed:
            destination.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest.append(dict(action='move',source=source.relative_to(root).as_posix(),
        target=destination.relative_to(root).as_posix(),original_sha256=hashlib.sha256(original).hexdigest()))

for source in sorted(root.rglob('closed_loop.*')):
    if source.suffix not in ('.json','.png','.svg','.dot'):
        continue
    target=source.with_name('closed_loop_system_online'+source.suffix)
    assert source.resolve().is_relative_to(root)
    assert target.resolve().is_relative_to(root)
    assert target.exists() and source.read_bytes()==target.read_bytes(),source
    manifest.append(dict(action='remove_identical_duplicate',source=source.relative_to(root).as_posix(),
        target=target.relative_to(root).as_posix(),sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    source.unlink()

for path in root.rglob('*'):
    if path.suffix not in ('.md','.html','.txt'):
        continue
    before=path.read_text(encoding='utf-8')
    after=re.sub(r'\bclosed_loop\.(json|png|svg|dot)\b',r'closed_loop_system_online.\1',before)
    after=re.sub(r'(?<!offline/)closed_loop_system_offline\.',r'offline/closed_loop_system_offline.',after)
    if after!=before:
        path.write_text(after,encoding='utf-8')

assert all(p.parent.name=='offline' for p in root.rglob('closed_loop_system_offline.*'))
assert not any(p.suffix in ('.json','.png','.svg','.dot') for p in root.rglob('closed_loop.*'))
Path('tmp/closed_loop_layout_migration.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Moved offline files:',sum(x['action']=='move' for x in manifest))
print('Removed identical online duplicates:',sum(x['action']=='remove_identical_duplicate' for x in manifest))

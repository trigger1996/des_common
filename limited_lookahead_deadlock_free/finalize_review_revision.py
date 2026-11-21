"""Refresh metadata and remove obsolete generated views after a review run."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from certified_benchmark import dump
from compare_online_offline import load_plant
from des_core.certified_lookahead import preprocess
from des_core.plot_automaton import render_plant
from examples.review_amendments import CHANGES,DEFERRED,REMOVED
from examples.yin_literature import build_yin_literature_examples

ROOT=Path('outputs/expanded_yin_benchmark')


def main():
    rows=json.loads((ROOT/'model_results.json').read_text(encoding='utf-8'))
    paper=[r for r in rows if not r['name'].startswith('structural_')]
    dump(ROOT/'model_summary.json',dict(literature_models=len(paper),structural_models=len(rows)-len(paper),
        total_models=len(rows),statuses=dict(Counter(r['status'] for r in rows))))
    summary=json.loads((ROOT/'summary.json').read_text(encoding='utf-8'))
    summary.update(paper_models=len(paper),statuses=dict(Counter(r['status'] for r in paper)),
        revision='User table amendments; original transcriptions retained separately.',
        deferred_conflicts=DEFERRED,removed_original_duplicates=REMOVED)
    dump(ROOT/'summary.json',summary)
    examples={e.name:e for e in build_yin_literature_examples()}
    sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    for source in sources:
        source['notes']=examples[source['name']].description
        source['user_amendments']=CHANGES.get(source['name'],[])
        source['deferred_conflict']=DEFERRED.get(source['name'])
    dump(ROOT/'sources.json',sources)
    mirror=Path('outputs/closed_loop_systems')
    archive=Path('tmp/user_review_revision_20261121/obsolete_gallery')
    for name in REMOVED:
        old=mirror/name;target=archive/name
        if old.exists():
            assert old.resolve().is_relative_to(mirror.resolve())
            assert target.resolve().is_relative_to(archive.resolve())
            target.parent.mkdir(exist_ok=True,parents=True)
            shutil.move(str(old),str(target))
    for r in rows:
        folder=ROOT/r['name'];plant=load_plant(folder);pre=preprocess(plant,max_path_visits=2_000_000)
        render_plant(plant,folder,r['name'],pre.deadlocks,pre.safe)
        if (mirror/r['name']).exists():shutil.copy2(folder/'plant.png',mirror/r['name']/'plant.png')
        if r['status']=='losing':
            paths=[folder/'closed_loop_system_online.dot',folder/'offline/closed_loop_system_offline.dot',
                   folder/'supervisor.png',folder/'supervisor.svg',folder/'supervisor_memory.csv',
                   folder/'supervisor_offline.png',folder/'supervisor_offline.svg',folder/'supervisor_offline_memory.csv']
            paths += [mirror/r['name']/name for name in ('closed_loop_system_online.dot','supervisor.png','supervisor.svg','supervisor_memory.csv')]
            for path in paths:
                if path.exists():path.unlink()
        bts=json.loads((folder/'offline/bts.json').read_text(encoding='utf-8'))
        if len(bts['D'])+len(bts['O'])>65 and (folder/'offline/bts.png').exists():
            (folder/'offline/bts.png').unlink()
        if (folder/'offline/plant.png').exists():(folder/'offline/plant.png').unlink()
    # Old mirror aliases predate the reviewed model; archive rather than leave
    # contradictory pictures next to the canonical online artifacts.
    for old in mirror.rglob('closed_loop.*'):
        if old.suffix not in ('.json','.png','.svg','.dot'):continue
        target=archive/'legacy_aliases'/old.relative_to(mirror)
        assert old.resolve().is_relative_to(mirror.resolve())
        assert target.resolve().is_relative_to(archive.resolve())
        target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(old),str(target))
    for row in json.loads((ROOT/'large_literature_supervisors.json').read_text(encoding='utf-8'))['results']:
        folder=ROOT/row['name'];source=ROOT/row['source_model'];plant=load_plant(source)
        pre=preprocess(plant,max_path_visits=2_000_000)
        render_plant(plant,folder,row['source_model']+f' | asynchronous product x {row["copies"]}',pre.deadlocks,pre.safe,
            subtitle=f'Component BEFORE product; full plant {row["reachable_product_states"]:,} states')
        shutil.copy2(folder/'plant.png',folder/'component_product_overview.png')
        shutil.copy2(source/'plant.png',folder/'component_plant.png')
    old=json.loads(Path('tmp/user_review_revision_20261121/model_results.json').read_text(encoding='utf-8'))
    old_status={r['name']:r['status'] for r in old}
    dump(ROOT/'review_revision_summary.json',dict(models=len(rows),statuses=dict(Counter(r['status'] for r in rows)),
        explicit_modified_models=len(CHANGES),removed_original_duplicates=REMOVED,deferred_conflicts=DEFERRED,
        changed_statuses=[dict(name=r['name'],before=old_status[r['name']],after=r['status']) for r in rows if old_status[r['name']]!=r['status']],
        large_offline_rerun=False,original_review_backup='tmp/user_review_revision_20261121',
        note='The two large literature results use revised component controllers and exact composition proofs; global minimal u not measured.'))
    report=['用户审阅修订后的论文模型运行结果',f'论文模型{len(paper)}个；另有3个结构测试；共{len(rows)}例。',
        str(dict(Counter(r['status'] for r in rows))),
        '全部逐例数值、公式和最小u见运行结果.md；修改请求及处理结果见系统事件属性与修改意见.md。',
        '原始转录保存在各例plant_original.json/png，按表新增/删除的边不冒充原论文拓扑。',
        '两个论文乘积放在large_systems；本轮未运行完整大系统offline。',
        '暂缓冲突：'+str(DEFERRED),'',
        'name | states | draft_u | decisive_u | matching_u | selected_u | status | D | O']
    report.extend(' | '.join(str(r[k]) for k in ('name','states','draft_u','minimal_decisive_u','minimal_matching_u','selected_u','status','D','O')) for r in rows)
    (ROOT/'report.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    with zipfile.ZipFile(mirror.parent/'closed_loop_systems.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in mirror.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(mirror.parent))
    print('Final metadata refreshed:',len(rows),dict(Counter(r['status'] for r in rows)), 'modified',len(CHANGES))


if __name__=='__main__':main()

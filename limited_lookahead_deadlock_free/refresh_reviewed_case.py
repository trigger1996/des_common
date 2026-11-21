"""Recalibrate a single amended case without rerunning the full corpus."""
import json
from pathlib import Path
import sys
from time import perf_counter

from certified_benchmark import dump,export_plant,export_bts,summary_row,trajectory
from des_core.certified_lookahead import preprocess,solve_certified,solve_offline,validate_policy
from examples.yin_literature import build_yin_literature_examples


def main(name):
    root=Path('outputs/expanded_yin_benchmark');folder=root/name
    example=next(e for e in build_yin_literature_examples() if e.name==name)
    export_plant(example,folder);pre=preprocess(example.dfa,max_path_visits=2_000_000)
    offline=solve_offline(example.dfa);sweep=[];started=perf_counter()
    for u in range(len(example.dfa.states)):
        r=solve_certified(pre,horizon=u);validate_policy(pre,r)
        same=(r.status,set(r.maximal_patterns))==(offline.status,set(offline.maximal_patterns))
        sweep.append(dict(u=u,status=r.status,D=r.decision_count,O=r.observation_count,edges=r.edge_count,
            seconds=r.seconds,same_offline_root_patterns=same,maximal_patterns=[sorted(p) for p in r.maximal_patterns]))
    selected=next(s['u'] for s in sweep if s['u']>=pre.horizon and s['same_offline_root_patterns'])
    r=solve_certified(pre,horizon=selected);validate_policy(pre,r)
    row=summary_row(name,pre,r,offline,selected,perf_counter()-started)
    row.update(minimal_decisive_u=next(s['u'] for s in sweep if s['status']!='inconclusive'),
        minimal_matching_u=next(s['u'] for s in sweep if s['same_offline_root_patterns']),
        source=example.source_name,notes=example.description,added_this_round=False)
    dump(folder/'preprocessing.json',dict(Qd=sorted(pre.deadlocks),Qf=sorted(pre.failure),Qe=sorted(pre.safe),
        draft_u=pre.horizon,minimal_decisive_u=row['minimal_decisive_u'],minimal_matching_u=row['minimal_matching_u'],selected_u=selected))
    export_bts(pre,r,folder)
    export_bts(pre,offline,folder/'offline',structure='BTS',draw=offline.decision_count+offline.observation_count<=65)
    for filename in ('paper_results.json','model_results.json'):
        rows=json.loads((root/filename).read_text(encoding='utf-8'))
        rows=[row if x['name']==name else x for x in rows];dump(root/filename,rows)
    for filename,value in (('u_sweeps.json',sweep),('trajectories.json',trajectory(pre,selected,steps=20))):
        data=json.loads((root/filename).read_text(encoding='utf-8'));data[name]=value;dump(root/filename,data)
    print(name,r.status,selected)


if __name__=='__main__':main(sys.argv[1])

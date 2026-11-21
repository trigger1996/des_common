"""Reproducible paper corpus, u sweep, offline comparison and random experiment.

Run: python certified_benchmark.py --samples 600 --seed 20261120
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys
from time import perf_counter
import tracemalloc

from des_core.automata import DFA, DESExample
from des_core.certified_lookahead import (preprocess, solve_certified, solve_offline,
                                         validate_policy, executable_choices, CertifiedController)
from examples.yin_literature import build_yin_literature_examples
from examples.non_deadlock import build_small_cycle_example, build_nested_cycle_deadlock_example


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def export_plant(example, folder):
    p = example.dfa
    dump(folder/'plant.json', {'name':example.name,'source':example.source_name,
         'notes':example.description,'states':sorted(p.states),'initial':p.initial,
         'events':sorted(p.events),'controllable':sorted(p.controllable),
         'observable':sorted(p.observable),
         'transitions':[[q,e,t] for (q,e),t in sorted(p.transitions.items())]})


def export_bts(pre, result, folder, *, draw=True, structure='LL-BTS'):
    if structure not in ('LL-BTS','BTS'):raise ValueError(structure)
    stem='bts' if structure=='BTS' else 'll_bts'
    estimates = sorted(result.constructed_choices, key=lambda x: (len(x), sorted(x)))
    ids = {x:'D%d'%i for i,x in enumerate(estimates)}
    observations = sorted({(c.closure,c.pattern) for v in result.constructed_choices.values() for c in v},
                          key=lambda x:(sorted(x[0]),sorted(x[1])))
    oids = {x:'O%d'%i for i,x in enumerate(observations)}
    d = [{'id':ids[x],'estimate':sorted(x),'retained':x in result.policy,
          'safe_terminal':x in result.safe_terminals} for x in estimates]
    retained_observations = {(c.closure,c.pattern) for cs in result.policy.values() for c in cs}
    obs = [{'id':oids[(x,p)],'estimate':sorted(x),'pattern_controllable':sorted(p),
            'retained':(x,p) in retained_observations,
            'pattern_full':sorted(p|pre.plant.uncontrollable)} for x,p in observations]
    edges = set()
    for x, choices in result.constructed_choices.items():
        for c in choices:
            node = oids[(c.closure,c.pattern)]
            edges.add((ids[x],node,','.join(sorted(c.pattern)) or '{}'))
            for e,y in c.successors:
                edges.add((node,ids[y],e))
    policy_edges = set()
    for x, choices in result.policy.items():
        for c in choices:
            node = oids[(c.closure,c.pattern)]
            policy_edges.add((ids[x],node,','.join(sorted(c.pattern)) or '{}'))
            policy_edges.update((node,ids[y],e) for e,y in c.successors)
    dump(folder/(stem+'.json'), {'structure':structure,'status':result.status,'u':result.horizon,'window':sorted(result.window),
         'initial':ids[result.initial],'D':d,'O':obs,'edges':sorted(edges),
         'boundary_choices':result.boundary_choices,'policy_edges':sorted(policy_edges),
         'maximal_root_patterns':[sorted(p) for p in result.maximal_patterns],
         'window_semantics':('Full known state set; no lookahead limit.' if structure=='BTS' else
            'Materialized/query states only: root Qe certificate may stop before Post expansion.'),
         'terminal_semantics':'No certificate terminals; complete known-system UR/NX.' if structure=='BTS' else
            'D subset Q_e: implicit enable-all continuation; no O expansion'})
    def quote(s): return json.dumps(s,ensure_ascii=False)
    lines=['digraph '+('BTS' if structure=='BTS' else 'LLBTS')+' {','rankdir=LR;','node [fontname="Arial"];']
    for n in d:
        label='{'+','.join(map(str,n['estimate']))+'}'
        if n['safe_terminal']:
            label+='\nSAFE: enable all'
        lines.append('%s [shape=box,label=%s,color=%s];'%(n['id'],quote(label),
                     'green' if n['safe_terminal'] else ('black' if n['retained'] else 'red')))
    for n in obs:
        label='{'+','.join(map(str,n['estimate']))+'}\nC={'+','.join(n['pattern_controllable'])+'}'
        lines.append('%s [shape=ellipse,label=%s,color=%s];'%(n['id'],quote(label),
                     'black' if n['retained'] else 'red'))
    lines += ['%s -> %s [label=%s];'%(a,b,quote(e)) for a,b,e in sorted(edges)]
    lines.append('}')
    (folder/(stem+'.dot')).write_text('\n'.join(lines),encoding='utf-8')
    if not draw:
        path=folder/(stem+'.png')
        if path.exists():path.unlink()
        return
    # Use networkx/matplotlib already required by the repository; no new packages.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import networkx as nx
    graph=nx.DiGraph()
    for n in d+obs: graph.add_node(n['id'])
    for a,b,e in edges:
        if graph.has_edge(a,b): graph[a][b]['label']+=','+e
        else: graph.add_edge(a,b,label=e)
    distances=nx.single_source_shortest_path_length(graph,ids[result.initial])
    layers={}
    for node in graph:
        level=distances.get(node,max(distances.values(),default=0)+1)
        layers.setdefault(level,[]).append(node)
    # Fixed layer spacing prevents equal-successor control choices from piling
    # on top of each other, as they do with a spring-force layout.
    width=max(8,(max(layers,default=0)+1)*2.1)
    height=max(5.5,max(map(len,layers.values()),default=1)*.85+2)
    fig,ax=plt.subplots(figsize=(width,height))
    pos={node:(level*2.1,(i-(len(nodes)-1)/2)*.85)
         for level,nodes in layers.items() for i,node in enumerate(nodes)}
    colors=['#b5dfc2' if n in {x['id'] for x in d if x['safe_terminal']} else
            '#b9d5ed' if n.startswith('D') else '#f7dfb0' for n in graph]
    labels={n['id']:n['id']+'\n{'+','.join(n['estimate'])+'}' for n in d}
    labels.update({n['id']:n['id']+'\n{'+','.join(n['estimate'])+'}\nC={'+
                   ','.join(n['pattern_controllable'])+'}' for n in obs})
    retained={n['id'] for n in d+obs if n.get('retained')}
    borders=['#333333' if n in retained else '#bf4545' for n in graph]
    nx.draw_networkx(graph,pos,ax=ax,labels=labels,node_color=colors,edgecolors=borders,
                     node_size=1700,font_size=6,arrowsize=15,width=.65,alpha=.85)
    nx.draw_networkx_edge_labels(graph,pos,nx.get_edge_attributes(graph,'label'),ax=ax,font_size=6)
    ax.set_title('%s | %s | %s\nD: estimates, O: estimate/control; red border: pruned; full labels in JSON/DOT'%
                 (folder.name,structure+(' | u='+str(result.horizon) if structure=='LL-BTS' else ''),result.status))
    ax.axis('off'); fig.tight_layout(); fig.savefig(folder/(stem+'.png'),dpi=150); plt.close(fig)
    if structure=='LL-BTS':
        from des_core.plot_automaton import render_plant
        render_plant(pre.plant,folder,folder.name,pre.deadlocks,pre.safe)



def summary_row(name, pre, result, baseline, selected_u, u_seconds):
    return {'name':name,'states':len(pre.plant.states),'transitions':len(pre.plant.transitions),
            'Qc':len(pre.plant.controllable),'Qo':len(pre.plant.observable),
            'Qd':len(pre.deadlocks),'Qf':len(pre.failure),'Qe':len(pre.safe),
            'draft_u':pre.horizon,'selected_u':selected_u,'path_visits':pre.path_visits,
            'status':result.status,'offline_status':baseline.status,
            'pre_seconds':pre.seconds,'online_seconds':result.seconds,
            'total_seconds':pre.seconds+result.seconds,'offline_seconds':baseline.seconds,
            'calibration_seconds_excluded':u_seconds,
            'D':result.decision_count,'O':result.observation_count,'edges':result.edge_count,
            'offline_D':baseline.decision_count,'offline_O':baseline.observation_count,
            'maximal_patterns':[sorted(p) for p in result.maximal_patterns],
            'same_maximal_patterns':set(result.maximal_patterns)==set(baseline.maximal_patterns)}


def random_plant(rng,index):
    n=rng.randint(4,12)
    states=[str(i) for i in range(n)]
    events=('a','b','c','o')
    mode=index%3
    controls=frozenset(e for e in events if rng.random()<.55)
    observable=frozenset(e for e in events if rng.random()<.55)
    # Both partitions nontrivial; no all-observable substitution.
    observable=(observable|{'o'})-{'a'}
    transitions={}
    probability=(.7,.45,.3)[mode]
    for q in states:
        if mode!=0 and rng.random()<.18:
            continue
        for e in events:
            if rng.random()<probability:
                transitions[q,e]=rng.choice(states)
        if mode==0 and not any(s==q for s,e in transitions):
            transitions[q,rng.choice(events)]=rng.choice(states)
    return DFA(frozenset(states),'0',frozenset(events),controls,observable,transitions)


def trajectory(pre,u,steps=12):
    controller=CertifiedController(pre,u)
    rows=[]
    for k in range(steps):
        belief=controller.estimate
        result,fresh,fallback=controller.solve()
        validate_policy(pre,result)
        row={'step':k,'estimate':sorted(belief),'seconds':fresh.seconds,'status':result.status,
             'fresh_status':fresh.status,'used_certified_continuation':fallback}
        rows.append(row)
        if result.status!='winning': break
        options=executable_choices(pre,result,belief)
        pattern=result.maximal_patterns[-1]
        choice=next(c for c in options if c.pattern==pattern)
        row['pattern']=sorted(pattern)
        if not choice.successors:
            row['stop']='no observable event; hidden continuation certified'
            break
        event,_=choice.successors[k%len(choice.successors)]
        belief=controller.observe(pattern,event)
        row['observation']=event; row['next_estimate']=sorted(belief)
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',type=int,default=600)
    parser.add_argument('--seed',type=int,default=20261120)
    parser.add_argument('--output',type=Path,default=Path('outputs/certified_yin_benchmark'))
    parser.add_argument('--no-plots',action='store_true')
    args=parser.parse_args(argv)
    out=args.output; out.mkdir(parents=True,exist_ok=True)
    corpus=build_yin_literature_examples()
    paper_rows=[]; sweeps={}; traces={}
    for e in corpus + (build_small_cycle_example(),build_nested_cycle_deadlock_example()):
        folder=out/e.name; folder.mkdir(exist_ok=True)
        export_plant(e,folder)
        pre=preprocess(e.dfa,max_path_visits=2_000_000)
        baseline=solve_offline(e.dfa)
        validate_policy(pre,baseline)
        sweep=[]; selected=None
        started=perf_counter()
        for u in range(len(e.dfa.states)):
            r=solve_certified(pre,horizon=u)
            validate_policy(pre,r)
            sweep.append({'u':u,'status':r.status,'D':r.decision_count,'O':r.observation_count,
                          'seconds':r.seconds,'maximal_patterns':[sorted(p) for p in r.maximal_patterns]})
            if selected is None and r.status!='inconclusive': selected=u
        calibration=perf_counter()-started
        assert selected is not None
        chosen=max(selected,pre.horizon)
        # selected is minimal decisive at the initial belief; chosen respects
        # the draft threshold. Calibration is experimental, not part of theorem.
        r=solve_certified(pre,horizon=chosen)
        assert r.status==baseline.status,(e.name,r.status,baseline.status)
        validate_policy(pre,r)
        row=summary_row(e.name,pre,r,baseline,chosen,calibration)
        row['minimal_decisive_u']=selected
        row['source']=e.source_name
        paper_rows.append(row); sweeps[e.name]=sweep
        dump(folder/'preprocessing.json',{'Qd':sorted(pre.deadlocks),'Qf':sorted(pre.failure),
             'Qe':sorted(pre.safe),'entries':sorted(pre.entries),'draft_u':pre.horizon,
             'selected_u':chosen,'minimal_decisive_u':selected})
        if not args.no_plots: export_bts(pre,r,folder)
        traces[e.name]=trajectory(pre,chosen)
        print(e.name,'u',pre.horizon,'->',chosen,r.status,flush=True)

    rng=random.Random(args.seed); random_rows=[]; budget_exceeded=[]
    for i in range(args.samples):
        p=random_plant(rng,i)
        try: pre=preprocess(p,max_path_visits=2_000_000)
        except RuntimeError:
            budget_exceeded.append(i); continue
        baseline=solve_offline(p)
        r=solve_certified(pre)
        validate_policy(pre,baseline); validate_policy(pre,r)
        if r.status=='winning': assert baseline.status=='winning'
        if r.status=='losing': assert baseline.status=='losing'
        full=solve_certified(pre,full=True)
        validate_policy(pre,full)
        assert (full.status,set(full.maximal_patterns))==(baseline.status,set(baseline.maximal_patterns))
        row=summary_row('random_%04d'%i,pre,r,baseline,pre.horizon,0.)
        row['full_certificate_seconds']=full.seconds
        row['full_certificate_D']=full.decision_count;row['full_certificate_O']=full.observation_count
        row['stratum']=('live','mixed','sparse')[i%3]
        if i<30:
            # Allocation peak measured separately, never mix traced timings into
            # the ordinary elapsed-time comparison. Input DFA already exists.
            tracemalloc.start(); solve_offline(p)
            row['offline_peak_python_bytes']=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
            tracemalloc.start(); mpre=preprocess(p); solve_certified(mpre)
            row['pre_plus_online_peak_python_bytes']=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        random_rows.append(row)
        if i%100==0: print('random',i,flush=True)
    dump(out/'paper_results.json',paper_rows); dump(out/'u_sweeps.json',sweeps)
    dump(out/'trajectories.json',traces); dump(out/'random_results.json',random_rows)
    keys=[k for k in paper_rows[0] if k!='maximal_patterns']
    with (out/'paper_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(paper_rows)
    summary={'seed':args.seed,'requested_random_samples':args.samples,'completed_random_samples':len(random_rows),
             'preprocessing_budget_exceeded':budget_exceeded,'paper_models':len(corpus),
             'project_models':2,'random_statuses':dict(Counter(r['status'] for r in random_rows)),
             'offline_statuses':dict(Counter(r['offline_status'] for r in random_rows)),
             'machine':platform.platform(),'python':sys.version,
             'semantics':'deadlock-free only, same count-pruning for both baselines; no result caching',
             'timing':'single fresh solve per random instance; population means, not worst-case guarantees; u sweep excluded'}
    for group in ['all','live','mixed','sparse']:
        rows=[r for r in random_rows if group=='all' or r['stratum']==group]
        if not rows:continue
        summary[group]={'n':len(rows),'decisive':sum(r['status']!='inconclusive' for r in rows)}
        for key in ('pre_seconds','online_seconds','total_seconds','offline_seconds','full_certificate_seconds'):
            values=[r[key] for r in rows]
            summary[group][key]={'mean':statistics.mean(values),'median':statistics.median(values),
                                 'max':max(values),'sum':sum(values)}
    originals={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path('.').rglob('*original*') if p.is_file()
               and p.name != 'original_hashes_after.json'}
    dump(out/'original_hashes_after.json',originals)
    dump(out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__': main()

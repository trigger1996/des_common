"""Actually synthesize and validate two >10^7-state literature products online.

No exhaustive offline BTS run. Full products remain exact factored transition
systems; component proofs cover all states, while small products are exhaustive
and large trajectories/witnesses independently exercise the exported supervisor.
"""
from collections import deque
from functools import lru_cache
import hashlib
import json
from math import prod
from pathlib import Path
import random
import statistics
from time import perf_counter
import tracemalloc
import gc

from certified_benchmark import dump,export_bts
from compare_online_offline import load_plant
from des_core.asynchronous_product import ImplicitProductDFA
from des_core.closed_loop import restore_certified_result
from literature_product_forecast import solve_online,verify_composition_small

ROOT=Path('outputs/expanded_yin_benchmark')
CASES=(('21AutomaticaOptimal_fig_2',6),('18TACrange_fig_3a',7))


def component_witnesses(component):
    paths={component.initial:[]};queue=deque(paths)
    while queue:
        q=queue.popleft()
        for event,target in component.enabled(q):
            if target not in paths:paths[target]=paths[q]+[event];queue.append(target)
    assert set(paths)==set(component.states)
    for target,events in paths.items():
        state=component.initial
        for event in events:state=component.transitions[state,event]
        assert state==target
    return paths


def exhaustive_small_products(component):
    rows=[]
    for copies in (1,2,3):
        product=ImplicitProductDFA(component,copies)
        states=0;transitions=0
        for state in product.states:
            enabled=product.enabled(state)
            assert enabled and len(enabled)>=copies
            for event,target in enabled:
                assert event in product.events and target in product.states
                raw,index=event.rsplit('_',1);index=int(index)
                expected=list(state);expected[index]=component.transitions[state[index],raw]
                assert target==tuple(expected)
                transitions+=1
            states+=1
        assert states==len(component.states)**copies
        assert transitions==copies*len(component.transitions)*len(component.states)**(copies-1)
        rows.append(dict(copies=copies,states=states,transitions=transitions,
                         exhaustive=True,deadlocks=0))
    return rows


def write_executable_controller(folder,descriptor):
    source='''"""Exported observation-feedback supervisor: a single memory state C0.

This controller never reads the actual DFA state. All events remain enabled.
"""
import json
from pathlib import Path


class Supervisor:
    def __init__(self):
        data=json.loads((Path(__file__).parent/'supervisor_online.json').read_text(encoding='utf-8'))
        self.memory='C0'
        self._enabled=frozenset(data['full_pattern'])
        self.observable=frozenset(data['observable'])

    def enabled_events(self):
        return self._enabled

    def observe(self,event):
        if event not in self.observable:
            raise ValueError('Only observable events are passed to observe().')
        self.memory='C0'
        return self.memory
'''
    (folder/'supervisor_online.py').write_text(source,encoding='utf-8')
    # Execute the EXPORTED artifact, not a separately coded surrogate policy.
    namespace={'__file__':str((folder/'supervisor_online.py').resolve())}
    exec(compile(source,str(folder/'supervisor_online.py'),'exec'),namespace)
    return namespace['Supervisor']


def run_large_trajectories(component,product,Supervisor,seed,trajectories=100,steps=1000):
    rng=random.Random(seed)
    @lru_cache(maxsize=256)
    def closure(estimate):
        reached=set(estimate);queue=deque(estimate)
        while queue:
            q=queue.popleft()
            for event,target in component.enabled(q):
                if event not in component.observable and target not in reached:
                    reached.add(target);queue.append(target)
        return frozenset(reached)
    @lru_cache(maxsize=1024)
    def observe(estimate,event):
        targets=frozenset(component.transitions[q,event] for q in estimate
                          if (q,event) in component.transitions)
        assert targets
        return closure(targets)
    counts=dict(trajectories=trajectories,steps_per_trajectory=steps,executed_steps=0,
        observable_events=0,hidden_events=0,deadlocks=0,disabled_uncontrollable_events=0,
        exact_factored_estimate_checks=0,max_estimate_cardinality=1,seed=seed)
    traces=[]
    for trial in range(trajectories):
        controller=Supervisor();state=product.initial
        estimates=[closure(frozenset((component.initial,))) for _ in range(product.copies)]
        trace=[]
        for step in range(steps):
            enabled=controller.enabled_events()
            assert product.uncontrollable<=enabled and enabled==product.events
            options=product.enabled(state)
            assert options
            event,target=rng.choice(options)
            assert event in enabled
            before=state;state=target
            base,index=event.rsplit('_',1);index=int(index)
            if event in product.observable:
                controller.observe(event)
                estimates[index]=observe(estimates[index],base)
                counts['observable_events']+=1
            else:counts['hidden_events']+=1
            # These factored estimates use ONLY observations, never actual q.
            assert all(q in estimate for q,estimate in zip(state,estimates))
            assert controller.memory=='C0'
            counts['exact_factored_estimate_checks']+=1
            counts['max_estimate_cardinality']=max(counts['max_estimate_cardinality'],prod(map(len,estimates)))
            counts['executed_steps']+=1
            if trial<3 and step<100:
                trace.append(dict(step=step,source=before,event=event,target=state,
                    observable=event in product.observable,memory=controller.memory,
                    local_estimates=[sorted(x) for x in estimates]))
        if trace:traces.append(dict(trajectory=trial,steps=trace))
    return counts,traces


def test_constructive_reachability(component,product,Supervisor,paths,seed,samples=1000):
    rng=random.Random(seed);states=sorted(component.states);transitions=0
    for _ in range(samples):
        target=tuple(rng.choice(states) for _ in range(product.copies))
        current=product.initial;controller=Supervisor()
        # Concatenating the indexed component reaching words constructively
        # reaches ANY tuple, by interleaving independence. Samples test code;
        # the all-tuples claim follows from the general construction.
        for index,local_target in enumerate(target):
            for event in paths[local_target]:
                indexed=event+'_'+str(index)
                assert indexed in controller.enabled_events()
                following=dict(product.enabled(current))[indexed]
                if indexed in product.observable:controller.observe(indexed)
                current=following;transitions+=1
        assert current==target
    return dict(target_tuples_tested=samples,actual_transitions_executed=transitions,seed=seed,
                all_tuple_reachability_proof='Concatenation of indexed component reaching words; no sampled inference.')


def render(folder,row):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    fig,ax=plt.subplots(figsize=(14,5));ax.axis('off')
    width=.84/row['copies'];left=.08
    for i in range(row['copies']):
        x=left+i*width
        ax.add_patch(FancyBboxPatch((x,.48),width*.78,.20,boxstyle='round,pad=.012',
            facecolor='#c6e1cd',edgecolor='#3f7750',transform=ax.transAxes))
        ax.text(x+width*.39,.58,f'G{i+1}\n{row["component_states"]} states',ha='center',va='center',
                fontsize=11,transform=ax.transAxes)
        if i+1<row['copies']:ax.text(x+width*.89,.58,'×',ha='center',va='center',fontsize=17,transform=ax.transAxes)
    ax.text(.5,.27,f'Supervisor C0: enable ALL events forever\n'
        f'{row["reachable_product_states"]:,} reachable closed-loop states | '
        f'{row["reachable_transitions"]:,} transitions\n'
        'Exact factored closed-loop representation, not a fully unrolled drawing.',
        ha='center',va='center',fontsize=12,transform=ax.transAxes)
    ax.set_title(row['source_model']+f' | {row["copies"]}-copy deadlock-free closed loop\n'
                 'Original partial observation and controllability retained',fontsize=14)
    fig.tight_layout();fig.savefig(folder/'closed_loop_system_online.png',dpi=150)
    fig.savefig(folder/'closed_loop_system_online.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4));ax.axis('off')
    ax.text(.5,.5,'D0: initial estimate\nQe-certified safe terminal\nEnable all events; no O expansion',
        ha='center',va='center',fontsize=14,transform=ax.transAxes,
        bbox=dict(boxstyle='round,pad=1',facecolor='#c6e1cd',edgecolor='#3f7750'))
    ax.set_title(f'Online LL-BTS | u={row["u"]} | winning',fontsize=14)
    fig.tight_layout();fig.savefig(folder/'ll_bts.png',dpi=150);fig.savefig(folder/'ll_bts.svg');plt.close(fig)


def run_case(source,copies):
    started=perf_counter();component=load_plant(ROOT/source)
    verify_composition_small(component)
    paths=component_witnesses(component)
    small=exhaustive_small_products(component)
    product=ImplicitProductDFA(component,copies)
    assert product.state_count>=10**7
    for attr in ('states','events','observable','controllable','uncontrollable'):getattr(product,attr)
    name=f'literature_product_{source}_{copies}copy';folder=ROOT/name;folder.mkdir(exist_ok=True)
    source_hash=hashlib.sha256((ROOT/source/'plant.json').read_bytes()).hexdigest()
    pre_times=[];solve_times=[];totals=[]
    for _ in range(101):
        pre,result,pt,st=solve_online(component,product)
        pre_times.append(pt);solve_times.append(st);totals.append(pt+st)
    gc.collect();tracemalloc.start();pre,result,_,_=solve_online(component,product)
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    export_bts(pre,result,folder,draw=False)
    saved=json.loads((folder/'ll_bts.json').read_text(encoding='utf-8'))
    saved.update(state_encoding='A product state is a tuple; inner JSON arrays decode to tuples.',
        window_construction='Root Qe certificate stops before window enumeration.',
        preprocessing='Exact compositional certificate; hidden DAG depth sum, not explicit product scan.')
    dump(folder/'ll_bts.json',saved)
    restored=restore_certified_result(pre,saved)
    assert restored.status=='winning' and restored.maximal_patterns==(product.controllable,)
    transitions=copies*len(component.transitions)*len(component.states)**(copies-1)
    descriptor=dict(name=name,source_model=source,source_file='../'+source+'/plant.json',
        source_sha256=source_hash,copies=copies,component_states=len(component.states),
        reachable_product_states=product.state_count,product_transitions=transitions,
        initial=product.initial,events=sorted(product.events),observable=sorted(product.observable),
        controllable=sorted(product.controllable),uncontrollable=sorted(product.uncontrollable),
        component_transitions=[[q,e,t] for (q,e),t in sorted(component.transitions.items())],
        composition='Exact asynchronous product; original partitions inherited; each e_i updates only coordinate i.')
    dump(folder/'plant_product.json',descriptor)
    dump(folder/'component_reachability_witnesses.json',paths)
    dump(folder/'supervisor_online.json',dict(status='winning',initial='C0',states=['C0'],
        full_pattern=sorted(product.events),controllable_pattern=sorted(product.controllable),
        observable=sorted(product.observable),rule='Enable all events; memory C0 never changes.',
        maximality='S/G = G; no supervisor can enable more than the full plant language.',
        source='ll_bts.json',source_model_sha256=source_hash))
    Supervisor=write_executable_controller(folder,descriptor)
    trajectory,trace=run_large_trajectories(component,product,Supervisor,20261121+copies)
    witness_test=test_constructive_reachability(component,product,Supervisor,paths,20261121)
    dump(folder/'simulation_samples.json',trace)
    dump(folder/'closed_loop_system_online.json',dict(status='winning',complete_symbolic_description=True,
        explicit_product_enumeration=False,reachable_states=product.state_count,reachable_transitions=transitions,
        controller_memory='C0',representation='Exact asynchronous product in plant_product.json with all events enabled.',
        proof='All component states reachable with recorded words. Indexed concatenation reaches any tuple. '
              'Every component state has at least one outgoing transition; hence every product state does. '
              'The supervisor disables none of them, so no plant- or control-induced deadlock exists.',
        source_model_sha256=source_hash))
    row=dict(name=name,source_model=source,copies=copies,component_states=len(component.states),
        reachable_product_states=product.state_count,reachable_transitions=transitions,
        events=len(product.events),controllable=len(product.controllable),observable=len(product.observable),
        status='winning',u=pre.horizon,D=result.decision_count,O=result.observation_count,
        synthesis_repetitions=101,pre_median_seconds=statistics.median(pre_times),
        solve_median_seconds=statistics.median(solve_times),total_median_seconds=statistics.median(totals),
        online_peak_python_bytes=peak,source_hash=source_hash,
        verification=dict(exhaustive_small_products=small,large_trajectory_tests=trajectory,
                          constructive_reachability_tests=witness_test),
        validation_scope='All-states mathematical certificate + complete component and small-product checks; '
                           'large random traces are additional tests, not the safety proof.',
        offline_complete=False,task_elapsed_seconds=perf_counter()-started)
    dump(folder/'actual_online_run.json',row)
    dump(folder/'actual_online_timing_samples.json',dict(pre_seconds=pre_times,solve_seconds=solve_times,total_seconds=totals))
    render(folder,row)
    write_case_report(folder,row)
    print(name,'winning',row['reachable_product_states'],'states;',trajectory['executed_steps'],'steps;',
          row['total_median_seconds']*1e6,'us',flush=True)
    return row


def write_case_report(folder,r):
    v=r['verification'];traces=v['large_trajectory_tests']
    lines=['# 实际 online 综合与闭环验证','',
        f'源例 `{r["source_model"]}`，{r["copies"]}副本异步乘积。结果：**winning，已得到可执行的无死锁 supervisor**。','',
        f'- 实际可达闭环状态：{r["reachable_product_states"]:,}；转移：{r["reachable_transitions"]:,}。',
        f'- 事件{r["events"]}，可控{r["controllable"]}，可观{r["observable"]}；原属性全部继承。',
        f'- u={r["u"]}；认证LL-BTS：D={r["D"]}，O={r["O"]}。',
        '- 监督器只有C0一个记忆状态，始终允许全部事件。它不读取真实物理状态，观测/隐藏事件均不改变控制。',
        '- 因所有分量状态都无死锁，乘积所有状态均有可用事件；全部允许不引入控制死锁。因此整个闭环无死锁。'
        '闭环语言就是完整plant语言，所以也是此目标下的最大宽松控制。','',
        '## 实际测量','',
        f'101次新鲜求解：组合式预处理中位数{r["pre_median_seconds"]*1e6:.3f} μs；'
        f'LL-BTS求解中位数{r["solve_median_seconds"]*1e6:.3f} μs；'
        f'逐次总时间中位数{r["total_median_seconds"]*1e6:.3f} μs。',
        f'另测Python分配峰值{r["online_peak_python_bytes"]:,} bytes。'
        '输入模型/公共索引、测试和绘图导出不计入综合耗时。',
        '采用精确组合式Qe证书，不是显式扫描千万状态；根证书在窗口展开前终止。'
        '只保证无死锁，不另加公平性、最终观测、标记非阻塞或原论文平均收益目标。','',
        '## 验证记录','',
        '| 分量副本数 | 完整枚举状态数 | 完整检查转移数 | 死锁数 |',
        '| ---: | ---: | ---: | ---: |']
    lines += [f'| {x["copies"]} | {x["states"]:,} | {x["transitions"]:,} | 0 |' for x in v['exhaustive_small_products']]
    lines += ['',f'- 在目标规模上执行{traces["trajectories"]}条、每条{traces["steps_per_trajectory"]}步的真实闭环轨迹，共'
        f'{traces["executed_steps"]:,}步，未见死锁或禁用不可控事件。',
        f'- 其中可观事件{traces["observable_events"]:,}、隐藏事件{traces["hidden_events"]:,}；'
        '每步校验按观测更新的精确因子化估计包含实际状态。',
        f'- 另构造并实际执行{v["constructive_reachability_tests"]["target_tuples_tested"]}个目标状态元组的到达串。'
        '记录的分量到达词可按坐标拼接到任意元组，故全状态可达性不是从随机样本推断。',
        '- 千万状态未逐一展开；完整闭环用精确因子化转移描述保存。随机运行只是额外测试，安全性由全状态组合证明保证。',
        '- 未运行完整offline BTS；此前的offline耗时估算不能当作完成实测。','',
        '文件：[监督器JSON](supervisor_online.json)、[可执行Python监督器](supervisor_online.py)、'
        '[完整因子化闭环](closed_loop_system_online.json)、[闭环图](closed_loop_system_online.svg)、'
        '[LL-BTS](ll_bts.png)、[实际测量与验证](actual_online_run.json)、[轨迹样本](simulation_samples.json)。']
    (folder/'SYNTHESIS_AND_VALIDATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (folder/'synthesis_index.html').write_text('<!doctype html><meta charset="utf-8"><title>实际无死锁综合结果</title>'
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto}img{max-width:100%}</style>'
        f'<h1>{r["source_model"]}：{r["copies"]}副本</h1><p>winning；{r["reachable_product_states"]:,}个可达闭环状态。'
        '单记忆状态监督器允许全部事件；按组合式Qe证书保证整个闭环无死锁。</p>'
        f'<p>含组合式预处理的实测综合总时间中位数：{r["total_median_seconds"]*1e6:.3f} μs。'
        '不包含验证/绘图。未逐一枚举千万状态，未运行完整offline BTS。</p>'
        '<p><a href="SYNTHESIS_AND_VALIDATION.md">完整方法与验证报告</a> · '
        '<a href="supervisor_online.py">可执行监督器</a> · <a href="actual_online_run.json">实际数据</a></p>'
        '<h2>认证LL-BTS</h2><img src="ll_bts.png"><h2>完整因子化闭环</h2>'
        '<img src="closed_loop_system_online.png">',encoding='utf-8')


def legacy_all_safe_main():
    started=perf_counter();rows=[run_case(source,copies) for source,copies in CASES]
    dump(ROOT/'large_literature_supervisors.json',dict(results=rows,total_task_seconds=perf_counter()-started))
    parts=['<!doctype html><meta charset="utf-8"><title>两个千万状态无死锁监督器</title>',
        '<style>body{font:16px system-ui;max-width:1200px;margin:30px auto}img{max-width:100%}</style>',
        '<h1>两个千万状态论文乘积：实际online综合与验证</h1>',
        '<p>均保留原部分观测/控制划分；以精确组合式Qe证书覆盖全乘积。'
        '完整闭环保存在因子化转移描述中，未逐状态展开；不把轨迹测试当作全系统安全证明。</p>']
    for r in rows:
        name=r['name']
        parts += [f'<h2>{r["source_model"]} × {r["copies"]}</h2><p>winning；'
            f'{r["reachable_product_states"]:,}状态；含组合式预处理{r["total_median_seconds"]*1e6:.3f} μs。'
            '完成100,000步目标规模闭环运行及小副本全状态验证。</p>',
            f'<p><a href="{name}/synthesis_index.html">查看该例结果</a> · '
            f'<a href="{name}/SYNTHESIS_AND_VALIDATION.md">验证报告</a> · '
            f'<a href="{name}/supervisor_online.py">可执行supervisor</a></p>',
            f'<img src="{name}/closed_loop_system_online.png">']
    (ROOT/'large_literature_supervisors.html').write_text('\n'.join(parts),encoding='utf-8')
    print('Both supervisors synthesized and validated; elapsed',perf_counter()-started,'seconds',flush=True)


def main():
    # The reviewed 18TACrange source has a deadlock; the old all-Qe route is
    # no longer applicable. Keep the command compatible with the new workflow.
    from revised_large_products import main as revised_main
    revised_main()


if __name__=='__main__':main()

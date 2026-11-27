"""Refresh large-system diagrams/catalogue from saved data; no offline solve."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import json
from pathlib import Path
from examples.benchmarks.certified_benchmark import dump
from des_core.automata import DFA
from des_core.plot_automaton import render_plant
from examples.non_deadlock import build_small_cycle_example

ROOT = Path('outputs/expanded_yin_benchmark/large_systems')


def main():
    lines = ['# 大系统目录、乘积前模型与运行口径', '',
        '本轮只重算两个修订后的论文乘积的online组合式综合；没有重新执行任何大型offline求解。'
        '其余四个系统沿用已有测量，明确标为历史数据。', '',
        '| 系统 | 构造方式 | 乘积前模型/模板 | 结果与测量 |',
        '| --- | --- | --- | --- |']

    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():continue

        name = folder.name

        if name.startswith('literature_product_'):
            d = json.loads((folder/'actual_online_run.json').read_text(encoding='utf-8'))
            lines.append(f'| {name} | {d["component_states"]}状态分量，异步乘积{d["copies"]}次；{d["reachable_product_states"]:,}个plant状态 | '
                f'[乘积前模型图]({name}/component_product_overview.png) | [本轮online综合与offline估算]({name}/SYNTHESIS_AND_VALIDATION.md) |')
        elif name.startswith('original_case1_product_'):
            d = json.loads((folder/'plant_product.json').read_text(encoding='utf-8'));copies = d['copies']
            p = build_small_cycle_example().dfa
            assert sorted([[q, e, t] for (q, e), t in p.transitions.items()]) == sorted(d['component_transitions'])
            render_plant(p, folder, f'Original case-1 | asynchronous product x {copies}',
                subtitle=f'Component BEFORE product; 6^{copies} = {d["global_states"]:,} reachable states')
            lines.append(f'| {name} | 6状态分量，异步乘积{copies}次 | [乘积前模型图]({name}/plant.png) | '
                '[历史预算内尝试与独立可行策略](LARGE_SYSTEM_COMPARISON.md#原七八副本异步乘积实际预算内尝试) |')
        elif name.startswith('large_'):
            terminal = 'finite_chain' in name
            n = json.loads((folder/'comparison.json').read_text(encoding='utf-8'))['states']
            successors = {('q'+str(i), 'o'):'q'+str(i+1) for i in range(5)}

            if not terminal:successors['q5', 'o'] = 'q3'

            p = DFA(frozenset('q'+str(i) for i in range(6)), 'q0', frozenset({'o'}), frozenset(), frozenset({'o'}), successors)
            render_plant(p, folder, 'Six-state SHAPE TEMPLATE | length scaling, NOT a Cartesian product',
                deadlocks={'q5'} if terminal else set(), subtitle=f'Actual indexed graph: {n:,} states; no multiplication count applies')
            lines.append(f'| {name} | 链长度扩展至{n:,}状态；不是异步乘积，6^k仅表示目标规模 | [6状态形状模板]({name}/plant.png) | [历史完整测量](LARGE_SYSTEM_COMPARISON.md) |')

    lines += ['', '## 旧实验说明', '',
        '两个索引链系统的offline/online历史测量仍在 LARGE_SYSTEM_COMPARISON.md 中，不能作为本轮重新实测。'
        '原case-1七/八副本的BTS尝试均因预算截断；其verified_feasible_closed_loop.json是另行验证的可行常量策略，不能宣称为完整最大宽松BTS综合结果。',
        '两个论文乘积的初始plant规模与监督后闭环规模分别报告。全局最小u未扫描；表中分量u不是全局最小u。']
    (ROOT/'LARGE_SYSTEM_OVERVIEW.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':main()

"""Numerical substitutions into explicit cost models, not invented seconds."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import json
from math import ceil
from pathlib import Path

from examples.comparisons.compare_online_offline import load_plant
from des_core.certified_lookahead import preprocess

ROOT = Path('outputs/expanded_yin_benchmark')


def cost_model(n, m, c, s, D, O, E, A, H, B, R, path_visits=0, hidden_indegree=0, prune_passes=1, online=False):
    # All coefficients equal one in this ABSTRACT operation/reference-slot
    # model. These values are not runtime predictions or CPython byte bounds.
    pre = n+m+s+(path_visits+1)*(hidden_indegree+1) if online else 0
    window = D*(n+m+s) if online else 0
    urnx = B*(n+m+s)
    pruning = prune_passes*(D+A+H)
    root_filter = R*R*(c+1)
    slots = n*D+(n+c)*O+E+(n+c)*A+n*H+(n+m+s if online else 0)
    # One explicit alternative encoding: packed bitsets, 1-byte node kind,
    # uint64 endpoints and uint32 edge symbol. Not the current Python layout.
    bq = ceil(n/8);bc = ceil(c/8)
    packed = D*(bq+1)+O*(bq+bc+1)+20*E

    return dict(n=n, m=m, c=c, s=s, P=2**c, D=D, O=O, E=E, A=A, H=H, B=B, R=R,
        path_visits=path_visits, hidden_max_indegree=hidden_indegree,
        preprocessing_work_proxy=pre, window_work_proxy=window, urnx_work_proxy=urnx,
        pruning_work_proxy=pruning, root_filter_work_proxy=root_filter,
        total_work_proxy=pre+window+urnx+pruning+root_filter,
        storage_reference_slot_proxy=slots, packed_logical_graph_bytes=packed)


def collect_model(name):
    folder = ROOT/name;plant = load_plant(folder);pre = preprocess(plant, max_path_visits=2_000_000)
    detail = json.loads((folder/'online_offline_comparison.json').read_text(encoding='utf-8'))
    n = len(plant.states);m = len(plant.transitions);c = len(plant.controllable);P = 2**c
    hidden_indegree = {q:0 for q in plant.states}

    for (q, e), t in plant.transitions.items():
        if e not in plant.observable:hidden_indegree[t] += 1

    values = {}

    for side in ('online', 'offline'):
        bts = json.loads((folder/('ll_bts.json' if side == 'online' else 'offline/bts.json')).read_text(encoding='utf-8'))
        d = detail[side+'_storage'];initial = bts['initial']
        expandable = (sum(not x['safe_terminal'] and not set(x['estimate'])&(pre.deadlocks|pre.failure) for x in bts['D'])
                    if side == 'online' else len(bts['D']))
        safe_root = any(x['id'] == initial and x['safe_terminal'] for x in bts['D'])
        root_patterns = {e[2] for e in bts['policy_edges'] if e[0] == initial}
        R = 1 if safe_root else len(root_patterns)
        values[side] = cost_model(n, m, c, len(plant.events), d['D'], d['O'], d['edges'], d['choice_records'], d['successor_incidences'],
            B=P*expandable, R=R, path_visits=pre.path_visits if side == 'online' else 0,
            hidden_indegree=max(hidden_indegree.values(), default=0),
            prune_passes=1 if side == 'offline' or bts['status'] == 'winning' else 2, online=side == 'online')

    return dict(name=name, **values, actual_online_peak_bytes=detail['online_peak_python_bytes'],
        actual_offline_peak_bytes=detail['offline_peak_python_bytes'])


def methodology(root):
    data = json.loads((root/'complexity_memory_calculation.json').read_text(encoding='utf-8'))
    example = next(r for r in data['models'] if r['name'] == '15ACCopac_fig_1')
    on = example['online'];off = example['offline']
    lines = ['### 总表的计算方法、理论时间与空间复杂度 / Calculation Methods and Theoretical Time and Space Complexity', '',
        '“最小u”分为最小可判定值与恢复offline根极大模式的最小值；“采用u”另满足草稿阈值。'
        'Δ均为Offline−Online，节约率为Δ÷Offline；百分数在显示时再乘100%。',
        '**信息节点：** N=|D|+|O|。D是决策估计节点，O是估计/控制模式节点；总表统计剪枝前构建过的逻辑节点。'
        'ΔN=N_BTS−N_LL-BTS，节点节约率=ΔN/N_BTS；D/O列按“D数/O数”显示。Plant状态数、信息节点数与闭环状态数分别统计，剪枝后保留节点见逐例分析。',
        '**理论时间：** n=|Q|，m=|δ|，c=|Σc|，s=|Σ|，P=2^c。令A为实际存储的估计—模式记录数、H为其观测后继关联数，B为执行UR/NX的模式检查次数，R为初始节点参与极大模式筛选的候选数。',
        r'传统BTS：$T_B=O(B_B(n+m+s)+D_B+A_B+H_B+R_B^2(c+1))$，其中$B_B=P D_B$。',
        r'在线LL-BTS：$T_L=O(C_{pre}+(n+m+s)+B_L(n+m+s)+D_L+A_L+H_L+R_L^2(c+1))$。'
        'B_L=P×实际展开模式的D节点数；Qe终端及直接失败节点不枚举模式。不能用保存的A_L代替B_L，因被提前拒绝的模式仍花费UR/NX时间。',
        '这些式子按已建索引、逻辑节点ID及集合基本操作的抽象模型计；字母表固定或s≤m时可简写n+m。当前Python还有排序、集合哈希/比较等表示开销：逐模式排序的保守附加项为online O(B_L(n log n+o log o))、offline O(B_B o log o)，o=|Σo|。',
        '预处理包含死锁/Qf/Qe扫描及不可观测最长简单路径搜索。若V为实际路径访问次数、d_h为不可观测最大入度，路径部分为O(V(d_h+1))，另有O(n+m+s)扫描与排序。'
        'V最坏可呈阶乘级；不能由窗口较小就推导online总时间在所有系统上更低。',
        '**理论值如何代入：** 报告给每例实际n,m,c,s,D,O,E,A,H,B,R,V，代入上述各项。'
        '在系数统一取1、忽略排序及集合表示开销的抽象模型中，定义W=B(n+m+s)+k(D+A+H)+R²(c+1)+C_pre_proxy+C_window；'
        '其中online的C_pre_proxy=n+m+s+(V+1)(d_h+1)，C_window=D(n+m+s)，逐决策估计重新建窗；offline两项为0，k为剪枝轮数。'
        'W是工作量代理，不是操作指令数、毫秒或完整Big-O的精确值，也不用于替代实测节约率。',
        f'例如15ACCopac_fig_1：n={on["n"]},m={on["m"]},c={on["c"]},s={on["s"]},P={on["P"]}；'
        f'BTS D/O={off["D"]}/{off["O"]}、N={off["D"]+off["O"]}，LL-BTS D/O={on["D"]}/{on["O"]}、N={on["D"]+on["O"]}；'
        f'减少{off["D"]+off["O"]-on["D"]-on["O"]}节点，节点节约率={(off["D"]+off["O"]-on["D"]-on["O"])/(off["D"]+off["O"]):.3%}。'
        f'抽象工作量W_B={off["total_work_proxy"]:,}、W_L={on["total_work_proxy"]:,}；逐项代入见详细报告。',
        r'**理论空间：** 当前实现保守计为$S_B=O(nD_B+(n+c)O_B+E_B+(n+c)A_B+nH_B)$；'
        r'$S_L=O(nD_L+(n+c)O_L+E_L+(n+c)A_L+nH_L+(n+m+s))$。'
        '最后一项为online预处理/窗口的额外存储；共同输入O(n+m+s)在两侧实测中均排除。'
        'nD与(n+c)O考虑估计/模式集合的编码；A/H项考虑实际实现的重复记录与后继估计，不能只数逻辑节点。',
        '**内存如何计算：** 实测M_on、M_off来自两次独立tracemalloc峰值测量，前置gc.collect，tracemalloc.start后分别运行预处理+online、完整offline求解，再读取peak。'
        'ΔM=M_off−M_on；内存节约率=ΔM/M_off。1 KiB=1024 bytes。计入运行中新分配的Python对象、集合、记录及临时工作区；不计共同已建DFA/索引、文件和绘图，不等于RSS，不覆盖所有C扩展内存。',
        '另给一种明确编码假设：状态估计用⌈n/8⌉字节位集、控制模式用⌈c/8⌉字节位集、节点种类1字节、每条逻辑边20字节。'
        '紧凑图编码估算M_graph=D(⌈n/8⌉+1)+O(⌈n/8⌉+⌈c/8⌉+1)+20E；它不含A/H重复记录、预处理和Python容器开销，不能当作当前实现的实际峰值。',
        '[每例理论参数、数值代入和内存计算明细](COMPLEXITY_AND_MEMORY_CALCULATION.md) · '
        '[随机自动机平均性能实验](randomized_comparison/RANDOMIZED_COMPARISON.md)', '']

    return '\n'.join(lines)


def main():
    models = json.loads((ROOT/'model_results.json').read_text(encoding='utf-8'))
    rows = [collect_model(r['name']) for r in models]
    dump = dict(models=rows, scope='Logical constructed graph; abstract work/reference-slot proxies and hypothetical packed graph bytes are not measured runtime/peak memory.')
    (ROOT/'complexity_memory_calculation.json').write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 理论复杂度、数值代入与内存计算', '', methodology(ROOT), '## 逐例代入参数与结果', '',
        'Online表项含预处理工作量代理及O(n+m+s)预处理存储槽代理；offline不做这些预处理。表中“槽数”不是字节；“紧凑图字节”是假定另一种编码的估算，最后一列才是当前Python实现实测峰值。', '',
        '| 系统/算法 | n/m/c/s | D/O/E | A/H/B/R | V | 抽象工作量W | 存储槽数代理 | 紧凑图字节估算 | 实测峰值bytes |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']

    for r in rows:
        for side, label in (('online', 'LL-BTS'), ('offline', 'BTS')):
            d = r[side]
            lines.append(f'| {r["name"]}/{label} | {d["n"]}/{d["m"]}/{d["c"]}/{d["s"]} | {d["D"]}/{d["O"]}/{d["E"]} | '
                f'{d["A"]}/{d["H"]}/{d["B"]}/{d["R"]} | {d["path_visits"]} | {d["total_work_proxy"]:,} | '
                f'{d["storage_reference_slot_proxy"]:,} | {d["packed_logical_graph_bytes"]:,} | {r["actual_"+side+"_peak_bytes"]:,} |')

    example = next(r for r in rows if r['name'] == '15ACCopac_fig_1')
    lines += ['', '## 完整数值代入示例：15ACCopac_fig_1', '']

    for side, label in (('online', 'LL-BTS'), ('offline', 'BTS')):
        d = example[side]
        lines += [f'{label}：UR/NX项B(n+m+s)={d["B"]}×({d["n"]}+{d["m"]}+{d["s"]})={d["urnx_work_proxy"]}；'
            f'剪枝项={d["pruning_work_proxy"]}；根筛选项={d["root_filter_work_proxy"]}；预处理代理={d["preprocessing_work_proxy"]}；窗口项={d["window_work_proxy"]}。'
            f'合计W={d["total_work_proxy"]}。']

    (ROOT/'COMPLEXITY_AND_MEMORY_CALCULATION.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('Calculated theoretical parameters for', len(rows), 'models; no timing rerun.')


if __name__ == '__main__':main()

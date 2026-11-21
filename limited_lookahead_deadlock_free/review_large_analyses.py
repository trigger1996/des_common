"""Markdown results for the revised, controlled component products."""
import json
from pathlib import Path
from benchmark_review_results import event_set,marked


def format_large_analyses(root,rows,existing):
    lines=['## 千万状态论文乘积：实际运行结果与分析','',
        '这两个论文乘积已移入 `large_systems/`，源例采用本轮修改后的模型。先综合一个分量的认证LL-BTS与supervisor，再复用到各独立副本；组合证明覆盖完整乘积。'
        '没有显式枚举全局LL-BTS，也没有求解完整offline BTS；计时包含共享分量预处理、求解、闭环构建及组合证书检查。',
        '[全部6个大系统的构造、乘积前模型图及历史/本轮结果入口](large_systems/LARGE_SYSTEM_OVERVIEW.md)。其中两个索引链系统是长度扩展，不是乘积，不伪造乘积次数。','',
        '| 源模型 × 副本数 | Plant可达状态 | 监督后物理状态 | 含记忆闭环状态 | Online/ms | Python峰值/bytes | 分量采用u | 全局最小u |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in rows:
        lines.append(f'| {r["source_model"]} × {r["copies"]} | {r["reachable_product_states"]:,} | '
            f'{r["closed_loop_physical_states"]:,} | {r["closed_loop_states"]:,} | {r["total_median_seconds"]*1000:.6f} | '
            f'{r["online_peak_python_bytes"]:,} | {r["component_u"]} | 未测，不冒充最小值 |')
    for r in rows:
        name=r['name'];short=Path(name).name
        d=json.loads((root/name/'plant_product.json').read_text(encoding='utf-8'))
        events=set(d['events']);observed=set(d['observable']);controls=set(d['controllable'])
        lines+=['',f'### {short}','',
            f'源例 `{r["source_model"]}`：{r["component_states"]}状态，异步乘积 **{r["copies"]}次**。'
            f'乘积规模={r["component_states"]}^{r["copies"]}={r["reachable_product_states"]:,}。',
            f'![乘积之前的分量图，乘积{r["copies"]}次]({name}/component_product_overview.png)','',
            '| 属性 | 集合 |','| --- | --- |',
            '| 可观事件 Σo | '+event_set(observed)+' |',
            '| 不可观事件 Σuo | '+event_set(events-observed)+' |',
            '| 可控事件 Σc | '+event_set(controls)+' |',
            '| 不可控事件 Σuc | '+event_set(events-controls)+' |','',
            '**综合结论与控制行为：** 两例均得到可执行的组合式无死锁supervisor。每个坐标只处理自己的事件；不可观事件不改变该坐标的控制器记忆。'
            '逐一验证分量闭环所有状态有允许出边且保留不可控事件，因此完整异步乘积也满足这两个条件。',
            f'分量LL-BTS构建D={r["component_D"]}、O={r["component_O"]}；采用u={r["component_u"]}。'
            '这里只保存并复用分量结构，不能把分量节点数当作显式全局LL-BTS节点数。',
            f'监督后的物理状态={r["closed_loop_physical_states"]:,}；含控制器记忆的闭环状态={r["closed_loop_states"]:,}；闭环转移={r["closed_loop_transitions"]:,}。',
            f'101次新鲜运行总时间中位数={r["total_median_seconds"]*1000:.6f} ms；另测Python分配峰值={r["online_peak_python_bytes"]:,} bytes。'
            '输入、绘图和轨迹测试不计时；结构可用于online，也可用于优化后的offline。',
            '额外验证：1/2/3副本全可达状态与转移检查，以及导出supervisor实际运行100条×1000步。'
            '完整乘积的保证来自组合证明，轨迹抽样是补充验证。']
        if r['source_model']=='18TACrange_fig_3a':
            lines+=['本轮新增 `8′─c1→9′`、删除 `10─o→8` 后，状态10成为死锁。原来的“所有状态都在Qe、永远允许全部事件”证书已失效，旧结果已归档。'
                '新supervisor在相应观测记忆下禁用危险的c2，避免进入10；分量闭环保留10个物理状态，因此7副本监督后恰有10^7个物理状态。']
        lines+=['', '**Offline复杂度与粗估：** 令N为乘积状态数、M为乘积转移数、C为可控事件数。传统BTS估计节点最坏可达2^N−1，逐模式UR/NX时间上界O(2^C·2^N·(N+M))；这是最坏上界，不是实际规模预测。',
            f'根模式数2^C={r["offline_root_patterns"]:,}。假设紧凑输入每条转移16 bytes、每状态8 bytes，显式plant本身约{r["explicit_input_compact_bytes"]/(1024**3):.3f} GiB；'
            '不含BTS或Python对象开销，不能与online新分配峰值直接计算节约率。',
            f'假设扫描吞吐率100万～1000万条转移/秒，仅扫描{r["reachable_transitions"]:,}条转移约{r["explicit_input_scan_seconds_range"][0]:.2f}～{r["explicit_input_scan_seconds_range"][1]:.2f}秒。'
            '该区间按M÷吞吐率计算，是假定吞吐率的粗估，不是实测offline总时间；未跑完整BTS，无法可靠给出其总耗时或实测节约百分比。']
        if 'offline_root_forecast' in r:
            f=r['offline_root_forecast']
            lines+=[f'此例源设计未变，历史实测单模式根检查{f["sample_median_seconds"]*1000:.6f} ms，乘{f["patterns"]:,}个模式，'
                f'外推根阶段≈{f["seconds"]:,.3f}秒≈{f["seconds"]/86400:.2f}天、根记录≈{f["bytes"]/(1024**4):.2f} TiB。'
                '完整offline没有运行，内存更可能先不足；共享闭包、位集、符号模式族或组合优化都会改变该估算。']
        lines+=['',f'[详细验证报告]({name}/SYNTHESIS_AND_VALIDATION.md) · [可执行supervisor]({name}/supervisor_online.py) · '
            f'[精确因子化闭环]({name}/closed_loop_system_online.json) · [分量闭环图]({name}/closed_loop_system_online.svg) · '
            f'[原始实测]({name}/actual_online_run.json)','',
            '#### 修改意见（请填写）','',marked('USER-NOTES',short,existing.get(short,'- 源例或副本数调整：\n- 可观/可控事件调整：\n- 希望保留的闭环或预期行为：\n- 其他意见：'))]
    return '\n'.join(lines)

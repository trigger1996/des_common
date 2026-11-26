"""Create/update the requested Markdown event catalogue, preserving user notes."""

from collections import Counter
import json
from pathlib import Path
import re
import shutil

from benchmark_review_results import enrich_review, split_review

ROOT = Path('outputs/expanded_yin_benchmark')
TARGET = ROOT/'系统事件属性与修改意见.md'
RESULTS = ROOT/'运行结果.md'
LEGACY = ROOT/'系统事件属性与运行结果与修改意见.md'


def event_set(events):
    return '`{'+', '.join(sorted(events))+'}`' if events else '∅'


def main():
    source = TARGET if TARGET.exists() else LEGACY
    previous = source.read_text(encoding='utf-8') if source.exists() else ''
    existing = {name:text for name, text in re.findall(
        r'<!-- USER-NOTES: (.*?) -->\n(.*?)\n<!-- END-USER-NOTES: .*? -->', previous, re.S)}
    from examples.review_amendments import CHANGES, DEFERRED, REMOVED

    modifications = {r['name']:r for r in json.loads((ROOT/'review_modifications.json').read_text(encoding='utf-8'))} if (ROOT/'review_modifications.json').exists() else {}

    if modifications:
        from complexity_memory_report import main as refresh_cost_model

        refresh_cost_model()

    def disposition(name):
        if name in DEFERRED:return '冲突待处理：'+DEFERRED[name]

        if name in CHANGES:return '已按表修改并重新计算'

        if name == '16SEI_fig_4b':return '保留原结构；初始1为综合失败状态，但不属于当前局部Qf充分判据'

        if name == '21AutomaticaOptimal_fig_2':return '保留原结构；本轮使用正整数前视，判定/匹配及采用值见运行结果'

        if name in ('16TACuniform_fig_1a', '16TACuniform_fig_1c', '16TACuniform_fig_3a', '18TACrange_fig_3b', '24AutoOpt_fig_1'):
            return '未发现相同的带事件属性结构，保留并重新计算'

        return '未要求拓扑变更，保留结构并重新计算'

    order = json.loads((ROOT/'model_results.json').read_text(encoding='utf-8'))
    models = []

    for row in order:
        folder = ROOT/row['name']
        plant = json.loads((folder/'plant.json').read_text(encoding='utf-8'))
        bts = json.loads((folder/'ll_bts.json').read_text(encoding='utf-8'))
        closed = json.loads((folder/'closed_loop_system_online.json').read_text(encoding='utf-8')) if (folder/'closed_loop_system_online.json').exists() else None
        models.append((row, plant, bts, closed))

    single = [row['name'] for row, p, b, c in models if len(p['states']) == 1]
    # The deletion condition concerns original plant states, not a collapsed
    # LL-BTS certificate or the closed loop extracted by one specific strategy.
    assert len(single) <= 1, 'Multiple one-state plants found: reconcile source registry before removal.'
    audit = dict(criterion='len(plant.json.states) == 1', models_checked=len(models),
        single_state_plants=single, retained=single[:1], removed=[],
        single_node_ll_bts=[r['name'] for r, p, b, c in models if len(b['D'])+len(b['O']) == 1],
        single_state_closed_loops=[r['name'] for r, p, b, c in models if c and len(c['nodes']) == 1],
        explanation='No original one-state plants found; no deletion needed.' if not single else
                    'Only one original one-state plant exists; retained.')
    (ROOT/'single_state_plant_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 原始系统事件属性与修改意见', '',
        '所有论文例子均以原始系统设计为基础，统一改编为本基准的无死锁综合任务；按快速索引逐例执行拓扑及事件属性修改。未要求改边的例子保留原结构，不能将其说成全部都改过拓扑。',
        '事件划分以当前 `plant.json` 为准；`plant_original.json/png` 保留本轮修改前的转录。新填意见不会自动执行。',
        '论文来源未给出可控划分时所采用的测试设定、集中式观测适配等，仍以每例来源备注为准。',
        '可观/不可观与可控/不可控是两组独立划分。事件名称 `uc`、`u` 或 `h` 本身不决定其属性，请按下面的集合判断。', '',
        '- Σ：全部事件；Σo：可观事件；Σuo = Σ − Σo：不可观事件。',
        '- Σc：可控事件；Σuc = Σ − Σc：不可控事件（控制器始终允许）。',
        '- `winning` 表示当前无死锁目标可解；`losing` 表示当前模型下不可解。',
        '- 每例保留了独立的“修改意见”区；重新运行生成脚本时会保留区内已有内容。', '',
        f'共 {len(models)} 个当前系统，其中 {sum(r.get("group")=="structural" for r,p,b,c in models)} 个为结构测试；另有3个原始重复设计已移出活动基准。',
        f'当前单状态原始 plant 数量：{len(single)}。'+('没有按单状态plant条件移出的模型；去重处理另见下表。' if not single else '已只保留一个。'),
        '单节点 LL-BTS 或单状态闭环不等于单状态 plant，不纳入此项删除。详见 `single_state_plant_audit.json`。', '',
        '## 快速索引', '',
        '- [x] 按表修改、逐例重算并保留原始设计快照。',
        '- [x] 运行结果中新增总表，列出最小u、时间/内存具体差值和节约率及公式。',
        '- [x] 两个论文大乘积统一移入 `large_systems/`，提供乘积前分量图及副本数；不运行完整offline。',
        '- [x] 检查重复设计并移出3例；保留原请求及去重依据。',
        '- [x] 原冲突意见均已按后续修正执行；20CDC2_fig_2b 已加2的b自环、6的c自环，当前没有待处理冲突。', '',
        '| 序号 | 系统 | 状态数 | 可观事件 Σo | 可控事件 Σc | 当前结果 | 原修改意见 | 处理结果 |',
        '| --- | --- | ---: | --- | --- | --- | --- | --- |']

    for i, (r, p, b, c) in enumerate(models, 1):
        name = r['name']
        lines.append(f'| {i} | [{name}](#{name.lower()}) | {len(p["states"])} | '
            f'{event_set(p["observable"])} | {event_set(p["controllable"])} | {b["status"]} | '
            f'{modifications.get(name,{}).get("request", "") or "—"} | {disposition(name)} |')

    lines += ['', '### 去重与暂缓处理', '',
        '去重比较的是修改前的初始状态、转移结构及事件的可观/可控属性；允许状态/事件重命名，忽略从未出现在转移上的字母。移出的原设计及旧结果归档在 `tmp/user_review_revision_20261121/removed_examples/`，不再计入活动基准。',
        '| 移出例子 | 保留代表 | 依据 |', '| --- | --- | --- |']

    for name, representative in REMOVED.items():
        lines.append(f'| {name} | [{representative}](#{representative.lower()}) | 修改前带事件属性的结构同构；代表例子按本轮意见修改后可能与旧设计不同 |')

    for i, (r, p, b, c) in enumerate(models, 1):
        name = r['name'];events = set(p['events']);observed = set(p['observable']);controls = set(p['controllable'])
        lines += ['', f'## {name}', '',
            f'编号：{i}。类别：'+('用户指定结构测试。' if r.get('group') == 'structural' else '论文自动机。'),
            f'原始状态数：{len(p["states"])}；转移数：{len(p["transitions"])}；初始状态：`{p["initial"]}`。',
            f'当前结果：`{b["status"]}`；所选前视深度：`u={b["u"]}`。', '',
            '| 事件属性 | 集合 |', '| --- | --- |',
            '| 全部事件 Σ | '+event_set(events)+' |',
            '| 可观事件 Σo | '+event_set(observed)+' |',
            '| 不可观事件 Σuo | '+event_set(events-observed)+' |',
            '| 可控事件 Σc | '+event_set(controls)+' |',
            '| 不可控事件 Σuc | '+event_set(events-controls)+' |', '',
            f'[原始系统图]({name}/plant.png) · [原始系统数据]({name}/plant.json) · '
            f'[LL-BTS]({name}/ll_bts.png) · [闭环结果]({name}/closed_loop_system_online.png)', '',
            '来源：'+str(p.get('source') or '项目例子')+'。', '',
            '模型备注：'+str(p.get('notes') or '无')+'。', '',
            f'[修改前原始设计]({name}/plant_original.json) · [修改前原图]({name}/plant_original.png)', '',
            '本轮处理：'+disposition(name)+'。', '',
            '### 修改意见（请填写）', '', f'<!-- USER-NOTES: {name} -->',
            existing.get(name, '- 需要修改的状态或转移：\n- 可观事件调整：\n- 可控事件调整：\n- 希望保留的闭环或预期行为：\n- 其他意见：'),
            f'<!-- END-USER-NOTES: {name} -->']

    # Preserve the existing text verbatim outside generated analysis sections,
    # including comments the user may have added outside the note markers.
    if modifications:
        lines += ['', '## 已移出例子的原修改意见（保留）', '']

        for name in REMOVED:
            lines.extend([f'### {name}', '', f'<!-- USER-NOTES: {name} -->', existing.get(name, ''), f'<!-- END-USER-NOTES: {name} -->', ''])

    text = enrich_review('\n'.join(lines)+'\n' if modifications else previous or '\n'.join(lines)+'\n', ROOT, models, existing)
    analysis_count = text.count('<!-- RUN-RESULTS:')
    text, results = split_review(text)
    after = {name:value for name, value in re.findall(
        r'<!-- USER-NOTES: (.*?) -->\n(.*?)\n<!-- END-USER-NOTES: .*? -->', text, re.S)}
    assert all(after.get(name) == value for name, value in existing.items()), 'User notes changed'

    if previous:
        assert source.read_text(encoding='utf-8') == previous, 'Review document changed during generation; retry to incorporate it.'
        backup = Path('tmp/review_results_split_20261121');backup.mkdir(parents=True, exist_ok=True)

        if not (backup/'original_review.md').exists():shutil.copy2(source, backup/'original_review.md')

    staged = TARGET.with_suffix('.md.tmp');staged.write_text(text, encoding='utf-8')
    staged.replace(TARGET)
    results_staged = RESULTS.with_suffix('.md.tmp');results_staged.write_text(results, encoding='utf-8')
    results_staged.replace(RESULTS)

    if source == LEGACY and LEGACY.exists():LEGACY.unlink()

    (ROOT/'review_document_validation.json').write_text(json.dumps(dict(
        file=TARGET.name, results_file=RESULTS.name, original_models=len(models), preserved_user_note_blocks=len(existing),
        total_user_note_blocks=len(after), run_analysis_blocks=analysis_count,
        legacy_name_exists=LEGACY.exists()), ensure_ascii=False, indent=2), encoding='utf-8')
    print('Written', TARGET, 'models', len(models), 'preserved notes', len(existing),
          'single-state plants', single)


if __name__ == '__main__':main()

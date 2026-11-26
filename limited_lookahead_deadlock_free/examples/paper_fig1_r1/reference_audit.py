"""Numerically audit the manually transcribed labels of Figs/R1/ll-bts.r1.pdf.

PDF geometry is inspected visually; claimed sources and state labels below
are explicit transcription, not an assertion of automatic arrow extraction.
UR, NX, liveness, and retained patterns are then checked programmatically.
"""

import hashlib
import json

from des_core.certified_lookahead import complete_choice
from examples.paper_fig1_r1.incremental_merge import ordered


def states(*indices):
    return frozenset('q_' + str(index) for index in indices)


X0 = states(0)
X6 = states(6)
XM = states(6, 8, 11)


def show(values):
    return '{' + ','.join(q.replace('_', '') for q in ordered(values)) + '}'


def audit_reference(pre, result, record, folder, reference, horizon):
    # Sources follow the drawn arrows. The four rows marked "mixed_source"
    # instead match XM; they are drawn from (q6,{q6}) in the supplied figure.
    claims = [
        ('R01 初始全模式', X0, {'a', 'b', 'o2'}, states(0, 1, 2, 3, 4, 5), None),
        ('R02 初始 a,o2', X0, {'a', 'o2'}, states(0, 1, 2, 3), None),
        ('R03 初始 a', X0, {'a'}, states(0, 1, 2, 3), None),
        ('R04 初始 b,o2', X0, {'b', 'o2'}, states(0), None),
        ('R05 三个混合估计决策的全模式', XM, {'a', 'b', 'o2'}, states(6, 7, 8, 9, 10, 11, 12, 13), None),
        ('R06 三个混合估计决策的 a,b', XM, {'a', 'b'}, states(6, 7, 8, 9, 10, 11, 12, 13), None),
        ('R07 单点 q6 的 a', X6, {'a'}, states(6, 7), None),
        ('R08 单点 q6 的全模式', X6, {'a', 'b', 'o2'}, states(6, 7, 12), None),
        ('R09 误接在单点 q6 下的 b,o2', X6, {'b', 'o2'}, states(6, 8, 9, 11), 'mixed_source'),
        ('R10 误接在单点 q6 下的 b', X6, {'b'}, states(6, 8, 9, 11), 'mixed_source'),
        ('R11 误接在单点 q6 下的 a,o2', X6, {'a', 'o2'}, states(6, 7, 8, 9, 10, 11), 'mixed_source'),
        ('R12 误接在单点 q6 下的 a', X6, {'a'}, states(6, 7, 8, 9, 10, 11), 'mixed_source'),
        ('R13 单点 q6 的 b,o2', X6, {'b', 'o2'}, states(6), None),
    ]
    rows = []

    for label, estimate, enabled, claimed, note in claims:
        pattern = frozenset(enabled)
        choice = complete_choice(pre.plant, estimate, pattern)
        gamma = pattern | pre.plant.uncontrollable
        blocked = frozenset(q for q in choice.closure
                            if not any(event in gamma for event, _ in pre.plant.enabled(q)))
        alternate = complete_choice(pre.plant, XM, pattern) if note else None
        row = dict(label=label, drawn_source_estimate=ordered(estimate),
                   gamma_c=sorted(pattern), gamma_full=sorted(gamma),
                   drawn_UR=ordered(claimed), computed_UR=ordered(choice.closure),
                   UR_matches=choice.closure == claimed,
                   computed_NX={event: ordered(target) for event, target in choice.successors},
                   blocked_states=ordered(blocked),
                   deadlock_states=ordered(choice.closure & pre.Q_d),
                   retained_at_drawn_source=any(c.pattern == pattern for c in result.policy.get(estimate, ())))

        if alternate:
            row.update(corrected_source_estimate=ordered(XM),
                       corrected_source_UR_matches=alternate.closure == claimed,
                       corrected_source_NX={event: ordered(target) for event, target in alternate.successors})

        rows.append(row)

    # A particular observable transition is possible only if its event is in
    # gamma and NX_event(UR_gamma(estimate)) is nonempty.
    forbidden_o2 = []

    for row in rows:
        if 'o2' not in row['gamma_full'] or 'o2' not in row['computed_NX']:
            forbidden_o2.append(row['label'])

    errors = [row for row in rows if not row['UR_matches']]
    assert len(errors) == 4
    assert all(row['corrected_source_UR_matches'] for row in errors)
    pure = complete_choice(pre.plant, X6, pre.plant.controllable)
    assert not pure.successors
    mixed_safe = complete_choice(pre.plant, XM, frozenset({'a'}))
    assert dict(mixed_safe.successors) == {'o1': X6}
    assert any(choice == mixed_safe for choice in result.policy.get(XM, ()))
    data = dict(verdict='The supplied figure is not fully correct as drawn.',
                source_pdf=str(reference), source_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
                transcription='Observation labels and source arrows manually transcribed from the supplied one-page PDF.',
                horizon=horizon, rows=rows, incorrect_source_UR_rows=len(errors),
                no_o2_successor_at_drawn_source=forbidden_o2,
                required_safe_mixed_successor=dict(estimate=ordered(XM), gamma_c=['a'],
                                                   UR=ordered(mixed_safe.closure), NX={'o1': ordered(X6)}))
    (folder / 'reference_claims_checked.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 参考图正确性核对', '',
        f'参考：`{reference}`；按本例 u={horizon} 的完整估计和 UR/NX 核验。原 PDF 未修改。', '',
        '**结论：这张图按当前连线并不完全正确。** 控制模式内含不可控事件 o1、u；下表的 gamma_c 只列可控部分。', '',
        '## 需要改正', '',
        '1. R09–R12 的四个观测状态接错了源决策。它们的 UR 对应 `{q6,q8,q11}`，'
        '不能从图中单点估计 `(q6,{q6})` 引出；应由三个混合估计决策状态分别引出。',
        '2. 三个混合估计决策必须保留 `gamma_c={a}` 的安全分支：'
        '`UR={q6,q7,q8,q9,q10,q11}`，`NX_o1={q6}`。图中若只给它们两个含 b 的坏分支，'
        '则初始全模式也会被反向剪除，不能继续作为保留模式。',
        '3. 不含 o2 的模式不能产生 o2 转移。特别是混合估计的 `{a,b,o1,u}` 只有 o1 后继，'
        '不能像图中那样用 o2 连到右侧坏决策。',
        '4. 从单点估计 `{q6}` 出发，任何控制模式都没有可观测后继；'
        '允许 a,b 时的 UR 为 `{q6,q7,q12}`，但 q6、q7、q12 都没有 o1/o2 出边。'
        '从这条分支画出的 o2 转移也应删除。',
        '5. 图中 q14 的叉号结论正确，但 q14 属于 Q_f，不是原始死锁 Q_d；'
        '新增 q14-a-q15-b-q16 后，该支仍没有无死锁延续。', '',
        '## 按本次合并规则统一', '',
        '- 初始 `{a,o1,u}` 与 `{a,o1,o2,u}` 的 UR 和全部后继相同，应保留较大的后者。',
        '- 单点 `{q6}` 的安全模式 `{a,o1,u}` 同理可用 `{a,o1,o2,u}` 代表；'
        'o2 在这条隐藏环上不发生，不能因此额外画 o2 后继。',
        '- 三个混合估计决策 `(q6,X)`、`(q8,X)`、`(q11,X)` 始终分别保存；'
        '不能因为它们采用相同控制就合并成一个 decision。', '',
        '## 逐项计算表', '',
        '| 图中位置 | 源估计 | gamma_c | 图中 UR | 计算 UR | 计算 NX | UR是否一致 |',
        '| --- | --- | --- | --- | --- | --- | --- |']

    for row in rows:
        nx = '; '.join(event + '→' + show(target) for event, target in row['computed_NX'].items()) or '无'
        lines.append('| ' + ' | '.join([row['label'], show(row['drawn_source_estimate']),
            '{' + ','.join(row['gamma_c']) + '}', show(row['drawn_UR']), show(row['computed_UR']), nx,
            '是' if row['UR_matches'] else '否：源决策接错']) + ' |')

    lines += ['', '## 合并后的实际决策状态与转移', '', '```text']

    for node in record['D']:
        if node['retained']:
            lines.append(node['id'] + ' = (' + node['q_hat'].replace('_', '') + ', ' + show(node['estimate']) + ')')

    for node in record['O']:
        if node['retained']:
            lines.append(node['id'] + ' = (' + show(node['estimate']) + ', {' + ','.join(node['pattern_full']) + '})')

    lines.extend(source + ' --' + event + '--> ' + target for source, target, event in record['policy_edges'])
    lines += ['```', '', '每次 merge_pattern 都在下一次候选模式生成之前执行；'
              '详见 construction_steps.jsonl 和逐步 PNG/GIF。', '']
    (folder / '参考图核对.md').write_text('\n'.join(lines), encoding='utf-8')

    return data

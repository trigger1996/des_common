"""Audit raw transition lists before converting them to dictionaries."""

from collections import defaultdict
import json
from pathlib import Path

ROOT = Path('outputs/expanded_yin_benchmark')


def audit(data, path):
    states = set(data['states']);events = set(data['events']);errors = []

    if len(states) != len(data['states']):errors.append('重复状态名称')

    if len(events) != len(data['events']):errors.append('重复事件名称')

    if not states or data['initial'] not in states:errors.append('初始状态不属于非空状态集')

    if not set(data['controllable']) <= events:errors.append('可控事件不属于事件集')

    if not set(data['observable']) <= events:errors.append('可观事件不属于事件集')

    successors = defaultdict(set);records = defaultdict(int)

    for q, e, t in data['transitions']:
        if q not in states or t not in states:errors.append(f'转移端点越界：{q},{e},{t}')

        if e not in events:errors.append(f'转移事件越界：{q},{e},{t}')

        successors[q, e].add(t);records[q, e, t] += 1

    conflicts = [dict(state=q, event=e, targets=sorted(targets)) for (q, e), targets in successors.items() if len(targets)>1]
    duplicates = [list(key) for key, count in records.items() if count>1]

    if duplicates:errors.append('存在重复转移记录')

    if conflicts:errors.append('同一状态同一事件存在多个后继')

    missing = len(states)*len(events)-len(successors)
    deadlocks = sorted(states-{q for q, e in successors})

    return dict(name=data['name'], file=path.as_posix(), valid_partial_dfa=not errors,
        errors=errors, conflicts=conflicts, duplicate_records=duplicates, states=len(states), events=len(events),
        transitions=len(data['transitions']), total_transition_function=missing == 0,
        undefined_state_event_pairs=missing, deadlock_states=deadlocks,
        eps_is_explicit_hidden_event='eps' in events and 'eps' not in data['observable'])


def main():
    models = json.loads((ROOT/'model_results.json').read_text(encoding='utf-8'))
    current = [audit(json.loads((ROOT/r['name']/'plant.json').read_text(encoding='utf-8')), ROOT/r['name']/'plant.json') for r in models]
    original_paths = list(ROOT.glob('*/plant_original.json'))
    original_paths += list(Path('tmp/user_review_revision_20261121/removed_examples').glob('*/plant_original.json'))
    original = [audit(json.loads(p.read_text(encoding='utf-8')), p) for p in original_paths]
    assert len(current) == 61 and len(original) == 64
    # Building the originals also executes _dfa's pre-dictionary duplicate-key
    # assertion; thus dictionary overwrites cannot hide source-list conflicts.
    from examples.yin_literature import build_yin_literature_examples

    assert len(build_yin_literature_examples(amended=False)) == 61
    large = []

    for path in (ROOT/'large_systems').glob('*/plant_product.json'):
        d = json.loads(path.read_text(encoding='utf-8'))
        entries = defaultdict(set)

        for q, e, t in d['component_transitions']:entries[q, e].add(t)

        assert all(len(v) == 1 for v in entries.values())
        large.append(dict(name=path.parent.name, valid_deterministic_product=True,
            reason='每个分量确定；事件按副本索引，单个全局事件只更新唯一坐标。'))

    errors = [r for r in current+original if not r['valid_partial_dfa']]
    report = dict(current_models=len(current), original_models=len(original), invalid_models=errors,
        original_determinism_checked_before_dictionary_conversion=True,
        current_total_dfa_count=sum(r['total_transition_function'] for r in current),
        original_total_dfa_count=sum(r['total_transition_function'] for r in original),
        current=current, original=original, large_products=large,
        deferred_requests=[], resolved_request=dict(name='20CDC2_fig_2b',
            retained=['2', 'c', '6'], added=[['2', 'b', '2'], ['6', 'c', '6']], applied=True))
    (ROOT/'dfa_definition_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# DFA定义与确定性复核', '',
        f'本轮检查{len(current)}个当前模型、{len(original)}个修改前模型：发现{len(errors)}个不符合确定性或数据合法性的模型。',
        '逐条读取原始转移列表后检查，未先转成字典；同时执行原始构造器的重复键断言，避免同事件多后继被覆盖后漏检。', '',
        '## 使用的定义', '',
        '本项目采用DES中的部分定义确定自动机：δ: Q×Σ ⇀ Q。每个状态—事件至多一个后继；允许某些事件未定义。',
        f'若采用教材中要求δ为全函数的完整DFA定义，当前{len(current)}例中只有{report["current_total_dfa_count"]}例完整；其余是部分DFA。',
        '终止状态、无出边状态、同一状态上不同事件的多条边、自环，以及不可达状态，都不违反这里的确定性定义。无死锁可解性是另一项性质。',
        '`eps`在Mealy例子中是显式事件名称，按不可观事件处理，不是无需事件发生的数学ε转移；不能把这些例子描述为含ε转移的普通DFA。', '',
        '## 已解决的修改意见', '',
        '`20CDC2_fig_2b`最新意见为添加 `2─b→2`、`6─c→6`，已执行；原有 `2─c→6` 保留。同一状态同一事件仍只有一个后继，当前没有暂缓冲突。',
        '`16WODESmax_fig_3a_Gprime`已按用户后续修正添加c2自环，原有c1出边保留，两种事件不同，无确定性冲突。', '',
        '| 当前模型 | 部分DFA合法 | 同状态同事件多后继 | 未定义状态—事件对数 | 无出边状态 |',
        '| --- | --- | ---: | ---: | --- |']

    for r in current:
        lines.append(f'| {r["name"]} | {"是" if r["valid_partial_dfa"] else "否"} | {len(r["conflicts"])} | {r["undefined_state_event_pairs"]} | '+(', '.join(r['deadlock_states']) or '无')+' |')

    lines += ['', '索引事件互不共享的异步乘积保持确定性；大系统检查分量及组合规则，不枚举千万状态。',
        '详细逐项数据见 [dfa_definition_audit.json](dfa_definition_audit.json)。']
    (ROOT/'DFA定义检查.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    assert not errors, errors
    print(json.dumps(dict(current=len(current), original=len(original), invalid=len(errors),
        total_current=report['current_total_dfa_count'], large_products=len(large)), ensure_ascii=False))


if __name__ == '__main__':main()

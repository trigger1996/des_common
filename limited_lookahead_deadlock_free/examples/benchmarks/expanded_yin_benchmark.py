"""Audit all literature models, calibrate u against offline root patterns, export BTSs.

python -X utf8 examples/benchmarks/expanded_yin_benchmark.py
The earlier 600-sample experiment is preserved in its original output directory.
"""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


from collections import Counter
import argparse
import csv
import hashlib
import json
from pathlib import Path

from examples.benchmarks.certified_benchmark import dump, export_plant, export_bts, summary_row, trajectory
from des_core.certified_lookahead import preprocess, solve_limited_lookahead, solve_offline, validate_policy
from examples.yin_literature import build_yin_literature_examples
from examples.yin_extended import build_yin_extended_examples


OUT = Path('outputs/expanded_yin_benchmark')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-plots', action='store_true', help='Export JSON/DOT without rendering PNGs')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = build_yin_literature_examples()
    additions = {e.name for e in build_yin_extended_examples()}
    rows, sweeps, sources, traces = [], {}, [], {}
    from time import perf_counter

    for example in corpus:
        plant = example.dfa
        folder = OUT/example.name
        folder.mkdir(exist_ok=True)
        export_plant(example, folder)
        pre = preprocess(plant, max_path_visits=2_000_000)
        offline = solve_offline(plant)
        validate_policy(pre, offline)
        sweep, decisive, matching = [], None, None
        started = perf_counter()

        for u in range(1, max(2, len(plant.states))):
            result = solve_limited_lookahead(pre, horizon=u)
            validate_policy(pre, result)

            if result.status != 'inconclusive':
                assert result.status == offline.status, (example.name, u)

                if decisive is None: decisive = u

            same = (result.status == offline.status and
                    set(result.maximal_patterns) == set(offline.maximal_patterns))

            if same and matching is None: matching = u

            sweep.append(dict(u=u, status=result.status, D=result.decision_count,
                O=result.observation_count, edges=result.edge_count,
                maximal_patterns=[sorted(p) for p in result.maximal_patterns],
                same_offline_root_patterns=same, seconds=result.seconds))

        calibration = perf_counter()-started
        assert decisive is not None and matching is not None
        # Select the first tested u meeting BOTH draft threshold and offline
        # equivalence; do not assume monotonicity of an untested depth.
        selected = next(s['u'] for s in sweep if s['u'] >= pre.horizon
                        and s['same_offline_root_patterns'])
        result = solve_limited_lookahead(pre, horizon=selected)
        validate_policy(pre, result)
        full = solve_limited_lookahead(pre, full=True)
        validate_policy(pre, full)
        assert (full.status, set(full.maximal_patterns)) == (offline.status, set(offline.maximal_patterns))
        row = summary_row(example.name, pre, result, offline, selected, calibration)
        row.update(minimal_decisive_u=decisive, minimal_matching_u=matching,
                   added_this_round=example.name in additions,
                   source=example.source_name, notes=example.description)
        rows.append(row); sweeps[example.name] = sweep
        dump(folder/'preprocessing.json', dict(Qd=sorted(pre.deadlocks), Qf=sorted(pre.failure),
            Qe=sorted(pre.safe), draft_u=pre.horizon, minimal_decisive_u=decisive,
            minimal_matching_u=matching, selected_u=selected))
        export_bts(pre, result, folder, draw=not args.no_plots)
        baseline_folder = folder/'offline'
        baseline_folder.mkdir(exist_ok=True)
        # Complete machine-readable offline BTS, including all control choices.
        # Large offline graphs remain DOT/JSON to avoid unreadable raster plots.
        export_bts(pre, offline, baseline_folder,
                   draw=not args.no_plots and offline.decision_count+offline.observation_count <= 65,
                   structure='BTS')
        traces[example.name] = trajectory(pre, selected, steps=20)
        pdfname = ('16TACuniform.pdf' if example.name.startswith('16TACuniform_') else
                   example.source_name.split('.pdf')[0]+'.pdf')
        pdf = Path('__ref/yin2016')/pdfname
        assert pdf.exists(), pdf
        sources.append(dict(name=example.name, figure=example.source_name,
            url='https://xiangyin.sjtu.edu.cn/Paper/'+pdfname,
            sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(), notes=example.description,
            transcription='Original visual figure audit, followed by user-authorized benchmark amendments; see review_modifications.json and plant_original.json.'))
        print(example.name, 'u', pre.horizon, '->', selected, result.status,
              'D/O', result.decision_count, result.observation_count, flush=True)

    dump(OUT/'paper_results.json', rows); dump(OUT/'u_sweeps.json', sweeps)
    dump(OUT/'sources.json', sources); dump(OUT/'trajectories.json', traces)
    inventory = json.loads(Path('__ref/yin2016/expanded_inventory.json').read_text(encoding='utf-8'))
    summary = dict(paper_models=len(rows), added_models=len(additions),
        source_papers=len({s['url'] for s in sources}),
        catalogue_entries=inventory['entries'], candidate_urls=len(inventory['downloads']),
        text_screened_pdfs=sum(d['status'] == 'text_screened' for d in inventory['downloads']),
        candidate_entries_without_pdf=[r['title'] for r in inventory['publications']
                                       if r['des_candidate'] and not r['urls']],
        failed_downloads=[d for d in inventory['downloads'] if d['status'] != 'text_screened'],
        statuses=dict(Counter(r['status'] for r in rows)),
        new_statuses=dict(Counter(r['status'] for r in rows if r['added_this_round'])),
        selected_u_range=[min(r['selected_u'] for r in rows), max(r['selected_u'] for r in rows)],
        same_offline_root_patterns=all(r['same_maximal_patterns'] for r in rows),
        limitation='Equivalence is root maximal-pattern equality for the deadlock-free objective; '
                   'not equivalence to original opacity, timing, attack, payoff or marking objectives.')
    dump(OUT/'summary.json', summary)

    with (OUT/'paper_results.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    lines = ['殷翔老师论文自动机扩充与 LL-BTS 测试（2026-11-21）',
        '官网目录：https://xiangyin.sjtu.edu.cn/publication.html',
        f"目录条目 {summary['catalogue_entries']}；DES候选PDF链接 {summary['candidate_urls']}；"
        f"完成全文文本筛查 {summary['text_screened_pdfs']}。",
        '目录检索覆盖所有列出的条目；不等于逐篇全文精读，也不能声称覆盖官网以外全部论文。',
        f"另有 {len(summary['candidate_entries_without_pdf'])} 条相关目录记录未附PDF链接（含会议/期刊重复版本），"
        '标题仍收录于总目录；未把它们计为已完成全文筛查。',
        f"自动机：34 -> {len(rows)}，新增 {len(additions)}，来源论文 {summary['source_papers']}。",
        '全部状态：'+str(summary['statuses'])+'；新增状态：'+str(summary['new_statuses']),
        '每例扫描 u=0..|Q|-1。selected_u 是同时满足草稿阈值和完整离线根极大控制模式一致的最小实测 u。',
        'minimal_decisive_u 只要求可判定；minimal_matching_u 另要求恢复离线根模式，二者分别记录。',
        '所有深度验证策略安全性，所有完整窗口核对离线根模式；winning 在线轨迹最多20步，逐步认证。',
        '新增验证类论文没有控制划分时，显式新增“全可控”测试设定；16SEI 使用集中式观测并集。详见 sources.json。',
        '当前为用户审阅后的改编模型；新增/删除边及事件属性调整详见review_modifications.json。plant_original.json保留原始转录。eps为显式不可观测输出符号。',
        '当前只测无死锁；非阻塞/标记、保密、安全禁区、时延、攻击、权重等原论文目标未复现。',
        '没有死锁可达的系统可由 Qe 证书直接终止：认证 LL-BTS 可能仅有一个 D 节点，这是有效压缩。',
        '每例目录：plant.json/png，preprocessing.json，ll_bts.json/dot/png。',
        'offline/bts.json/dot：传统完整离线 BTS（小于等于65节点时另有PNG）；不使用Qf/Qe证书。',
        'JSON 中 D/O 的 retained 标识剪枝保留情况；JSON/DOT完整记录构建图，PNG仅供辅助查看。',
        'u_sweeps.json：全部扫描；paper_results.csv/json：比较结果；sources.json：图号、URL、SHA256与适配说明。',
        '原600例随机实验输出保留于 outputs/certified_yin_benchmark/，本轮不以随机样本冒充新增论文模型。',
        '下载失败/缺失记录：'+json.dumps(summary['failed_downloads'], ensure_ascii=False),
        '', 'name | Q | E | draft_u | decisive_u | matching_u | selected_u | status | D | O']
    lines.extend(' | '.join(str(r[k]) for k in ('name', 'states', 'transitions', 'draft_u',
        'minimal_decisive_u', 'minimal_matching_u', 'selected_u', 'status', 'D', 'O')) for r in rows)
    (OUT/'report.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()

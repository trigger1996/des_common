"""Averages and agreement evidence from saved paired measurements."""

import statistics


def comparison_averages(rows, details):
    if not rows:raise ValueError('No paired models')

    n = len(rows)
    on = statistics.mean(r['online_total_median_seconds'] for r in rows)
    off = statistics.mean(r['offline_median_seconds'] for r in rows)
    on_mem = statistics.mean(r['online_peak_python_bytes'] for r in rows)
    off_mem = statistics.mean(r['offline_peak_python_bytes'] for r in rows)
    raw_on = [];raw_off = []

    for r in rows:
        s = details[r['name']]['samples']
        assert len(s['pre_seconds']) == len(s['online_seconds']) == len(s['offline_seconds'])
        raw_on.extend(a+b for a, b in zip(s['pre_seconds'], s['online_seconds']))
        raw_off.extend(s['offline_seconds'])

    ron = statistics.mean(raw_on);roff = statistics.mean(raw_off)
    means = dict(model_count=n, online_mean_model_median_seconds=on, offline_mean_model_median_seconds=off,
        mean_model_median_time_saved_seconds=off-on, mean_model_median_time_saving=(off-on)/off,
        online_mean_peak_python_bytes=on_mem, offline_mean_peak_python_bytes=off_mem,
        mean_peak_saved_bytes=off_mem-on_mem, mean_peak_saving=(off_mem-on_mem)/off_mem,
        online_mean_nodes=statistics.mean(r['online_nodes'] for r in rows),
        offline_mean_nodes=statistics.mean(r['offline_nodes'] for r in rows),
        raw_repetitions_per_side=len(raw_on), online_raw_mean_seconds=ron, offline_raw_mean_seconds=roff,
        raw_mean_time_saved_seconds=roff-ron, raw_mean_time_saving=(roff-ron)/roff,
        scope='First time mean averages the per-model medians in the main table. Raw time mean averages all saved individual repetitions. Mean memory averages separate per-model Python allocation peaks.')
    negative = {key:[r['name'] for r in rows if r[field]<0] for key, field in (
        ('time', 'time_saving_including_pre'), ('memory', 'peak_memory_saving'), ('nodes', 'node_saving'))}
    agreement = dict(models=n, complete_pairs=sum(r['decision_comparison_complete'] for r in rows),
        equal_decisions=sum(r['same_solvability_result'] for r in rows),
        offline_losing_count=sum(r['offline_status'] == 'losing' for r in rows),
        offline_losing_online_losing_count=sum(r['offline_status'] == 'losing' and r['online_status'] == 'losing' for r in rows),
        mismatched_models=[r['name'] for r in rows if not r['same_solvability_result']],
        semantics='Losing means proven no deadlock-free supervisor. Budget exceeded/inconclusive is not losing.')

    return dict(arithmetic_means=means, negative_savings=dict(counts={k:len(v) for k, v in negative.items()}, models=negative),
        decision_agreement=agreement)


def decision_metrics(online_status, offline_status):
    complete = online_status in ('winning', 'losing') and offline_status in ('winning', 'losing')

    return dict(online_status=online_status, offline_status=offline_status, decision_comparison_complete=complete,
        same_solvability_result=complete and online_status == offline_status,
        offline_losing_implies_online_losing=(online_status == 'losing') if offline_status == 'losing' else None)

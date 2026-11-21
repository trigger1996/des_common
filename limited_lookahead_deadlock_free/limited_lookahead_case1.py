from __future__ import annotations

from des_core.limited_lookahead import ExampleLookaheadReport, analyze_local_lookahead
from examples.non_deadlock import all_examples


def _format_belief(belief: frozenset[str]) -> str:
    return "{" + ",".join(sorted(belief)) + "}"


def print_report(report: ExampleLookaheadReport, horizon: int) -> None:
    print(f"\n[{report.name}] u={horizon}")
    print(
        "plant states/events: "
        f"{report.state_count}/{report.event_count}; "
        f"reachable estimates: {report.belief_count}; "
        f"control patterns: {report.control_pattern_count}"
    )
    print(
        "global upper bounds: "
        f"estimates <= {report.global_belief_upper_bound:,}, "
        f"decision-control pairs <= {report.global_pair_upper_bound:,}"
    )
    print(
        "local LL-BTS bounds: "
        f"max lookahead states = {report.max_local_states}, "
        f"max local pairs per estimate = {report.max_local_pairs}, "
        f"total evaluated local pairs = {report.total_local_pairs}"
    )

    for local in sorted(
        report.local_reports,
        key=lambda item: (-len(item.lookahead_states), _format_belief(item.belief)),
    )[:5]:
        print(
            "  "
            f"{_format_belief(local.belief)}: "
            f"|x_L|={len(local.lookahead_states)}, "
            f"good/bad/pending="
            f"{local.good_patterns}/{local.bad_patterns}/{local.pending_patterns}"
        )


def main() -> None:
    selected_names = {
        "example1_symbolic_cycles_full_partial_observation",
        "example2_nested_cycles_deadlock_full_partial_observation",
        "example3_possible_deadlock_full_partial_observation",
    }
    horizons = (1, 2, 3)
    examples = [example for example in all_examples() if example.name in selected_names]

    for example in examples:
        plant = example.original_dfa or example.dfa

        for horizon in horizons:
            print_report(analyze_local_lookahead(example.name, plant, horizon), horizon)


if __name__ == "__main__":
    main()

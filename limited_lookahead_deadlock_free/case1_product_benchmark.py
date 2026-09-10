from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from des_core.implicit_product import ProductIterationStats
from des_core.implicit_product import benchmark_case1_product, product_state_label
from examples.non_deadlock import build_small_cycle_example


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the case-1 product LL-BTS benchmark.")
    parser.add_argument("--copies", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--horizon", "-u", type=int, default=7)
    parser.add_argument("--quiet", action="store_true", help="Suppress per-iteration progress.")
    args = parser.parse_args()

    copies = args.copies
    iterations = args.iterations
    horizon = args.horizon
    default_run = copies == 8 and iterations == 200 and horizon == 7
    stem = (
        "case1_product_8copy"
        if default_run
        else f"case1_product_{copies}copy_u{horizon}_{iterations}iter"
    )
    output = Path("outputs") / f"{stem}_benchmark.txt"
    plot_output = Path("outputs") / f"{stem}_visited_states.png"
    plot_with_new_output = Path("outputs") / f"{stem}_visited_states_with_new.png"
    plot_paper_output = Path("outputs") / f"{stem}_visited_states_paper.pdf"

    example = build_small_cycle_example()
    global_state_count = len(example.dfa.states) ** copies
    progress = (
        None
        if args.quiet
        else lambda item, total, elapsed: _print_progress(
            item, total, elapsed, global_state_count
        )
    )
    if progress is not None:
        print(
            f"running complete LL-BTS benchmark: copies={copies}, "
            f"iterations={iterations}, u={horizon}",
            flush=True,
        )
    result = benchmark_case1_product(
        component=example.dfa,
        copies=copies,
        iterations=iterations,
        horizon=horizon,
        progress=progress,
    )

    lines = [
        "Case 1 implicit product benchmark",
        f"component states: {len(example.dfa.states)}",
        f"copies: {result.copies}",
        f"global product states: {result.global_state_count}",
        f"overall system lookahead limit u: {result.horizon}",
        f"iterations: {result.iterations}",
        f"elapsed seconds: {result.elapsed_seconds:.6f}",
        f"max LL-BTS concrete states per iteration: {result.max_local_states}",
        f"max states in decision estimates: {max((item.decision_estimate_state_count for item in result.stats), default=0)}",
        f"max states in observation estimates: {max((item.observation_estimate_state_count for item in result.stats), default=0)}",
        f"max decision information states: {max((item.decision_information_state_count for item in result.stats), default=0)}",
        f"max observation information states: {max((item.observation_information_state_count for item in result.stats), default=0)}",
        f"final cumulative visited states: {result.stats[-1].cumulative_state_count if result.stats else 0}",
        f"last new unique states: {result.stats[-1].new_state_count if result.stats else 0}",
        f"max LL-BTS edges per iteration: {result.max_local_edges}",
        "",
        "Selected iterations",
    ]
    selected = {0, 1, 2, 3, 4, 9, 24, 49, 74, result.iterations - 1}
    for item in result.stats:
        if item.iteration not in selected:
            continue
        lines.extend(
            [
                "",
                f"[iteration {item.iteration}]",
                f"current: {product_state_label(item.current)}",
                f"LL-BTS concrete states: {item.local_state_count}",
                f"states in decision estimates: {item.decision_estimate_state_count}",
                f"states in observation estimates: {item.observation_estimate_state_count}",
                f"decision information states: {item.decision_information_state_count}",
                f"observation information states: {item.observation_information_state_count}",
                f"new unique states: {item.new_state_count}",
                f"cumulative states: {item.cumulative_state_count}",
                f"LL-BTS edges: {item.local_edge_count}",
                f"selected event: {item.selected_event or '<none>'}",
                f"next: {product_state_label(item.next_state) if item.next_state else '<none>'}",
            ]
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _save_visited_state_plot(result, plot_with_new_output, include_new=True, paper_style=True)
    _save_visited_state_plot(result, plot_output, include_new=False, paper_style=True)
    _save_visited_state_plot(result, plot_paper_output, include_new=False, paper_style=True)
    print("\n".join(lines))
    print(f"\nreport written to: {output.resolve()}")
    print(f"plot written to: {plot_output.resolve()}")
    print(f"plot with new states written to: {plot_with_new_output.resolve()}")
    print(f"paper PDF plot written to: {plot_paper_output.resolve()}")


def _print_progress(
    item: ProductIterationStats,
    total_iterations: int,
    elapsed: float,
    global_state_count: int,
) -> None:
    percent = 100.0 * (item.iteration + 1) / max(total_iterations, 1)
    coverage = 100.0 * item.cumulative_state_count / max(global_state_count, 1)
    filled = int(round(percent / 5.0))
    bar = "#" * filled + "." * (20 - filled)
    print(
        f"[{bar}] [{item.iteration + 1:4d}/{total_iterations}] "
        f"{percent:6.2f}% elapsed={elapsed:8.1f}s "
        f"|Ihat|={item.decision_information_state_count:7d} "
        f"|I|={item.observation_information_state_count:7d} "
        f"D-est={item.decision_estimate_state_count:7d} "
        f"O-est={item.observation_estimate_state_count:7d} "
        f"new={item.new_state_count:7d} "
        f"cum={item.cumulative_state_count:7d} ({coverage:5.1f}%) "
        f"edges={item.local_edge_count:8d}",
        flush=True,
    )


def _save_visited_state_plot(result, output: Path, include_new: bool, paper_style: bool) -> None:
    iterations = [item.iteration for item in result.stats]
    local_counts = [item.local_state_count for item in result.stats]
    decision_estimate_counts = [item.decision_estimate_state_count for item in result.stats]
    observation_estimate_counts = [item.observation_estimate_state_count for item in result.stats]
    decision_info_counts = [item.decision_information_state_count for item in result.stats]
    observation_info_counts = [item.observation_information_state_count for item in result.stats]
    new_counts = [max(item.new_state_count, 1) for item in result.stats]
    cumulative_counts = [item.cumulative_state_count for item in result.stats]

    font_size = 15 if paper_style else 11
    label_size = 16 if paper_style else 12
    title_size = 17 if paper_style else 12
    legend_size = 13 if paper_style else 11
    line_width = 2.4 if paper_style else 2.0
    if paper_style and include_new:
        figsize = (7.16, 5.45)
    elif paper_style:
        figsize = (7.16, 4.55)
    else:
        figsize = (8.5, 5.2)

    with plt.rc_context(
        {
            "font.family": "serif",
            "mathtext.fontset": "cm",
            "axes.unicode_minus": False,
            "font.size": font_size,
            "axes.labelsize": label_size,
            "xtick.labelsize": font_size,
            "ytick.labelsize": font_size,
            "legend.fontsize": legend_size,
        }
    ):
        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(
            iterations,
            decision_estimate_counts,
            color="#1f77b4",
            linewidth=line_width,
            label=r"$\left|\cup_{\hat{\imath}\in\hat{\mathbb{I}}}\hat{x}\right|$",
        )
        ax.plot(
            iterations,
            observation_estimate_counts,
            color="#9467bd",
            linewidth=line_width,
            label=r"$\left|\cup_{\imath\in\mathbb{I}}x\right|$",
        )
        if include_new:
            ax.plot(
                iterations,
                decision_info_counts,
                color="#2ca02c",
                linewidth=1.8,
                alpha=0.9,
                label=r"$|\hat{\mathbb{I}}|$",
            )
            ax.plot(
                iterations,
                observation_info_counts,
                color="#ff7f0e",
                linewidth=1.8,
                alpha=0.9,
                label=r"$|\mathbb{I}|$",
            )
            ax.plot(
                iterations,
                new_counts,
                color="#4c4c4c",
                linewidth=1.7,
                linestyle="-.",
                alpha=0.9,
                label=r"new unique states",
            )
        else:
            ax.plot(
                iterations,
                cumulative_counts,
                color="#2ca02c",
                linewidth=line_width,
                label=r"cumulative concrete states",
            )
        ax.axhline(
            result.global_state_count,
            color="#d62728",
            linestyle="--",
            linewidth=line_width,
            label=rf"$|Q_{{\mathrm{{product}}}}|={result.global_state_count}$",
        )
        ax.set_xlabel(r"Iteration")
        ax.set_ylabel(r"Visited states")
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(mticker.LogLocator(base=10, numticks=8))
        ax.yaxis.set_minor_locator(
            mticker.LogLocator(base=10, subs=(2, 3, 5), numticks=18)
        )
        if include_new:
            positive_counts = [
                count
                for count in (
                    decision_estimate_counts
                    + observation_estimate_counts
                    + decision_info_counts
                    + observation_info_counts
                    + new_counts
                )
                if count > 0
            ]
            lower = max(1, min(positive_counts) * 0.65)
            ax.set_ylim(lower, result.global_state_count * 1.65)
        else:
            lower = max(1, min(local_counts) * 0.55)
            upper = result.global_state_count * 1.18
            ax.set_ylim(lower, upper)
        ax.grid(True, which="both", linestyle=":", linewidth=0.7, alpha=0.55)
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 1.01),
            ncol=3 if include_new else 2,
            framealpha=0.92,
            borderaxespad=0.0,
        )
        if not paper_style:
            ax.set_title(
                rf"Case 1 product benchmark ($u={result.horizon}$, {result.copies} agents)",
                loc="left",
                fontsize=title_size,
                fontweight="bold",
            )
        fig.subplots_adjust(left=0.12, right=0.985, bottom=0.115, top=0.84)
        fig.savefig(output, dpi=180, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)


if __name__ == "__main__":
    main()

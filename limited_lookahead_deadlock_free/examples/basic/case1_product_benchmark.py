from __future__ import annotations

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import argparse
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import matplotlib

matplotlib.use("Agg")  # This command writes figures and needs no GUI/Tk runtime.
# Embed TrueType fonts in PDF/PS output; IEEE/PaperCept preflight rejects Type 3 fonts.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from des_core.automata import DFA
from des_core.implicit_product import ProductIterationStats
from des_core.implicit_product import benchmark_case1_product, product_state_label
from des_core.visualization import save_original_system_png
from examples.non_deadlock import build_small_cycle_example


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the case-1 product LL-BTS benchmark.")
    parser.add_argument("--copies", type=int, default=7)
    parser.add_argument("--iterations", type=int, default=20, help="Maximum online iterations; Algorithm 2 may return earlier.")
    parser.add_argument("--horizon", "-u", type=int, default=2)
    parser.add_argument("--quiet", action="store_true", help="Suppress per-iteration progress.")
    parser.add_argument("--extra-plots", action="store_true", help="Also write auxiliary PNG plots.")
    parser.add_argument("--pattern-mode", choices=("explicit", "reduced", "factored"), default="factored")
    parser.add_argument("--cache-size", type=int, default=0, help="Optional identical-root result cache; disabled for timing by default.")
    parser.add_argument("--no-cache", action="store_true", help="Recompute every online iteration.")
    args = parser.parse_args()

    if args.copies < 1 or args.iterations < 1 or args.horizon < 0 or args.cache_size < 0:
        parser.error("copies/iterations must be positive and horizon nonnegative")

    copies = args.copies
    iterations = args.iterations
    horizon = args.horizon
    stem = f"case1_product_{copies}copy_u{horizon}_{iterations}iter_{args.pattern_mode}"
    stem += "_round-robin"

    if args.no_cache or args.cache_size == 0:
        stem += "_uncached"

    output_dir = Path("outputs") / stem
    output_dir.mkdir(parents=True, exist_ok=True)
    iteration_log = output_dir / "iterations.jsonl"
    iteration_log.write_text("", encoding="utf-8")

    def record_step(item: ProductIterationStats, _total: int, _elapsed: float) -> None:
        # Preserve completed steps even if a long run is interrupted later.
        with iteration_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(item)) + "\n")

    output = output_dir / "benchmark.txt"
    original_system_output = output_dir / "original_system.png"
    plot_output = output_dir / "visited_states.png"
    plot_with_new_output = output_dir / "visited_states_with_new.png"
    plot_paper_output = output_dir / "visited_states_paper.pdf"

    example = build_small_cycle_example()
    system_lines = _component_system_lines(example.dfa, copies)
    global_state_count = len(example.dfa.states) ** copies
    console = Console()

    if not args.quiet:
        console.print("\n".join(system_lines))
        console.print(
            f"[bold cyan]running single-branch LL-BTS product benchmark[/] "
            f"copies={copies}, iterations={iterations}, u={horizon}"
        )

    if not args.quiet:
        console.print(
            "Each uncached iteration constructs the local LL-BTS; single-branch "
            "refers only to the selected physical successor. "
            "D/O/frontier update during construction; coverage updates after each iteration."
        )

    if args.quiet:
        result = benchmark_case1_product(
            component=example.dfa,
            copies=copies,
            iterations=iterations,
            horizon=horizon,
            pattern_mode=args.pattern_mode,
            cache_size=0 if args.no_cache else args.cache_size,
            progress=record_step,
        )
    else:
        with _rich_progress(console) as progress_bar:
            task = progress_bar.add_task(
                "online iterations",
                total=iterations,
                coverage="0.0%",
                local="0",
                new="0",
                edges="0",
                expansion="preparing local window",
            )

            def update_progress(item: ProductIterationStats, total: int, elapsed: float) -> None:
                record_step(item, total, elapsed)
                _update_rich_progress(
                    progress_bar,
                    task,
                    item,
                    total,
                    elapsed,
                    global_state_count,
                )

            last_expansion_update = 0.0

            def update_expansion(decisions: int, observations: int, frontier: int) -> None:
                nonlocal last_expansion_update
                now = perf_counter()

                if frontier and now - last_expansion_update < 0.5:
                    return

                last_expansion_update = now
                progress_bar.update(
                    task, expansion=f"D={decisions:,} O={observations:,} frontier={frontier:,}"
                )

            result = benchmark_case1_product(
                component=example.dfa,
                copies=copies,
                iterations=iterations,
                horizon=horizon,
                pattern_mode=args.pattern_mode,
                cache_size=0 if args.no_cache else args.cache_size,
                progress=update_progress,
                expansion_progress=update_expansion,
            )

    lines = [
        "Case 1 implicit product benchmark",
        "",
        *system_lines,
        "",
        "Implicit product benchmark",
        f"component states: {len(example.dfa.states)}",
        f"copies: {result.copies}",
        f"global product states: {result.global_state_count}",
        f"overall system lookahead limit u: {result.horizon}",
        f"iterations: {result.iterations}",
        f"requested iterations completed: {result.iterations == iterations}",
        f"stop reason: {result.stop_reason}",
        "iteration count includes the final synthesis attempt, even if no successor is selected",
        f"pattern representation: {result.pattern_mode}",
        f"physical successor policy: {result.successor_policy}",
        "state/edge counts describe the represented graph before the final backward pass",
        "factored construction already prunes locally known inconsistent families",
        "reduced O counts are representatives; factored O counts are observable-choice families",
        "neither count is the number of full explicit observation information states",
        f"actual synthesis calls: {result.synthesis_calls}",
        f"identical-root cache hits: {result.cache_hits}",
        f"decision-observation cycle check: {result.cycle_check.message}",
        f"elapsed seconds: {result.elapsed_seconds:.6f}",
        f"max actual step seconds: {max(s.step_seconds for s in result.stats):.6f}",
        f"mean step seconds: {sum(s.step_seconds for s in result.stats) / len(result.stats):.6f}",
        f"max LL-BTS concrete states per iteration: {result.max_local_states}",
        f"max states in decision estimates: {max((item.decision_estimate_state_count for item in result.stats), default=0)}",
        f"max states in observation estimates: {max((item.observation_estimate_state_count for item in result.stats), default=0)}",
        f"max decision information states: {max((item.decision_information_state_count for item in result.stats), default=0)}",
        f"max observation information states: {max((item.observation_information_state_count for item in result.stats), default=0)}",
        f"final cumulative visited states: {result.stats[-1].cumulative_state_count if result.stats else 0}",
        f"last new unique states: {result.stats[-1].new_state_count if result.stats else 0}",
        f"max unique LL-BTS edges per iteration: {result.max_local_edges}",
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
                f"cache hit: {item.cache_hit}",
                f"step seconds: {item.step_seconds:.6f}",
                f"LL-BTS concrete states: {item.local_state_count}",
                f"states in decision estimates: {item.decision_estimate_state_count}",
                f"states in observation estimates: {item.observation_estimate_state_count}",
                f"decision information states: {item.decision_information_state_count}",
                f"observation information states: {item.observation_information_state_count}",
                f"new unique states: {item.new_state_count}",
                f"cumulative states: {item.cumulative_state_count}",
                f"unique LL-BTS edges: {item.local_edge_count}",
                f"selected event: {item.selected_event or '<none>'}",
                f"next: {product_state_label(item.next_state) if item.next_state else '<none>'}",
            ]
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "benchmark.json").write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    save_original_system_png(
        example.dfa,
        example.layout,
        original_system_output,
        title="case1 component original system",
    )

    if args.extra_plots:
        _save_visited_state_plot(result, plot_with_new_output, include_new=True, paper_style=True)
        _save_visited_state_plot(result, plot_output, include_new=False, paper_style=True)

    _save_visited_state_plot(result, plot_paper_output, include_new=False, paper_style=True)
    print("\n".join(lines))
    print(f"\noriginal component system PNG written to: {original_system_output.resolve()}")
    print(f"\nreport written to: {output.resolve()}")

    if args.extra_plots:
        print(f"plot written to: {plot_output.resolve()}")
        print(f"plot with new states written to: {plot_with_new_output.resolve()}")

    print(f"paper PDF plot written to: {plot_paper_output.resolve()}")


def _rich_progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=34, complete_style="green", finished_style="bold green"),
        MofNCompleteColumn(),
        TextColumn("[magenta]cov={task.fields[coverage]}"),
        TextColumn("[blue]local={task.fields[local]}"),
        TextColumn("[yellow]new={task.fields[new]}"),
        TextColumn("[red]edges={task.fields[edges]}"),
        TextColumn("{task.fields[expansion]}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def _component_system_lines(dfa: DFA, copies: int) -> list[str]:
    return [
        "Original component system",
        f"states: {', '.join(sorted(dfa.states))}",
        f"initial state: {dfa.initial}",
        f"events: {', '.join(sorted(dfa.events))}",
        f"controllable events: {_event_list(dfa.controllable)}",
        f"uncontrollable events: {_event_list(dfa.uncontrollable)}",
        f"observable events: {_event_list(dfa.observable)}",
        f"unobservable events: {_event_list(dfa.unobservable)}",
        f"product observable events: {_event_list(_product_events(dfa.observable, copies))}",
        f"product unobservable events: {_event_list(_product_events(dfa.unobservable, copies))}",
        f"product controllable events: {_event_list(_product_events(dfa.controllable, copies))}",
        f"product uncontrollable events: {_event_list(_product_events(dfa.uncontrollable, copies))}",
        "product setting: asynchronous interleaving; event controllability and observability inherit from the component",
        f"product control-pattern count: 2^{copies * len(dfa.controllable)} = {2 ** (copies * len(dfa.controllable))}",
        "transitions:",
        *_component_transition_lines(dfa),
    ]


def _component_transition_lines(dfa: DFA) -> list[str]:
    return [
        f"  {source} --{event}--> {target}"
        for (source, event), target in sorted(dfa.transitions.items())
    ]


def _product_events(events, copies: int) -> list[str]:
    return [
        f"{event}_{index}"
        for index in range(copies)
        for event in sorted(events)
    ]


def _event_list(events) -> str:
    ordered = sorted(events)

    return ", ".join(ordered) if ordered else "<none>"


def _update_rich_progress(
    progress: Progress,
    task_id,
    item: ProductIterationStats,
    total_iterations: int,
    elapsed: float,
    global_state_count: int,
) -> None:
    coverage = 100.0 * item.cumulative_state_count / max(global_state_count, 1)
    progress.update(
        task_id,
        completed=item.iteration + 1,
        total=total_iterations,
        coverage=f"{coverage:5.1f}%",
        local=f"{item.local_state_count:,}",
        new=f"{item.new_state_count:,}",
        edges=f"{item.local_edge_count:,}",
    )


def _save_visited_state_plot(result, output: Path, include_new: bool, paper_style: bool) -> None:
    iterations = [item.iteration for item in result.stats]
    local_counts = [item.local_state_count for item in result.stats]
    decision_estimate_counts = [item.decision_estimate_state_count for item in result.stats]
    observation_estimate_counts = [item.observation_estimate_state_count or float("nan") for item in result.stats]
    decision_info_counts = [item.decision_information_state_count for item in result.stats]
    observation_info_counts = [item.observation_information_state_count or float("nan") for item in result.stats]
    new_counts = [item.new_state_count if item.new_state_count else float("nan") for item in result.stats]
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
                label=(r"$|\mathbb{I}|$" if result.pattern_mode == "explicit" else "O families / representatives"),
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
        ax.set_ylabel("States / represented nodes" if include_new else "Visited concrete states")
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
            ax.set_ylim(lower, max([result.global_state_count] + positive_counts) * 1.65)
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

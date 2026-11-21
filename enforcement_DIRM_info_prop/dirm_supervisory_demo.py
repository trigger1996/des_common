"""Run every maintained DIRM supervisory-control example."""

from pathlib import Path
from dirm.supervisory_export import supervisory_diagnostics

from bts_comparasion import build_example_5_comparison, export_comparison
from dirm import (
    build_example_3_bts,
    build_example_4_bts,
    build_example_5_bts,
    build_example_6_bts,
    build_simplified_example_2_bts,
    build_user_example_1_bts,
    export_augmented_system,
    export_plant,
    export_supervisory_bts,
)


DEFAULT_OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "outputs"


def _run_example(
    name, builder, stem: str, plant_layout: str, output_directory: Path
) -> None:
    print(f"Starting {name}...", flush=True)
    bts = builder()
    plant_text, plant_image = export_plant(
        bts.plant, output_directory, f"{stem}_plant", layout=plant_layout,
        release_states=bts.system.release_states,
    )
    augmented_text, augmented_image = export_augmented_system(
        bts.system, output_directory, f"{stem}_augmented"
    )
    result = bts.synthesize()
    text_path, image_path = export_supervisory_bts(
        bts, output_directory, stem, result=result
    )
    print(
        f"{name}: structure={bts.structure}, states={dict(bts.state_counts())}, "
        f"reduced={dict(bts.reduction_stats)}, "
        f"winning={len(result.winning_states)}, "
        f"initial_winning={result.initial_winning}, "
        f"initial_controls={len(result.policy.get(bts.initial, ())) }\n"
        f"  original plant:    {plant_image} ({plant_text})\n"
        f"  augmented system:  {augmented_image} ({augmented_text})\n"
        f"  supervisory graph: {image_path} ({text_path})"
    )
    diagnostics = supervisory_diagnostics(bts, result)
    print(diagnostics, flush=True)
    report = output_directory / f"{stem}_diagnostics.txt"
    report.write_text(f"{name}\n{diagnostics}\n", encoding="utf-8")


def example_1(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Run Example 1, the corrected user-provided example."""
    _run_example(
        "Example 1 (user-provided DIRM example)",
        build_user_example_1_bts,
        "dirm_supervisory_example_1",
        "example_1",
        output_directory,
    )


def example_2(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Run Example 2, the simplified form of Example 1."""
    _run_example(
        "Example 2 (simplified user example)",
        build_simplified_example_2_bts,
        "dirm_supervisory_example_2",
        "example_2",
        output_directory,
    )


def example_3(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Run the independent project Example 3."""
    _run_example(
        "Example 3",
        build_example_3_bts,
        "dirm_supervisory_example_3",
        "example_3",
        output_directory,
    )


def example_4(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Run the independent project Example 4."""
    _run_example(
        "Example 4",
        build_example_4_bts,
        "dirm_supervisory_example_4",
        "example_4",
        output_directory,
    )


def example_5(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Run Example 5 and its two operator-swapped Y/Z AES comparisons."""
    _run_example(
        "Example 5 (release challenge)",
        build_example_5_bts,
        "dirm_supervisory_example_5",
        "example_5",
        output_directory,
    )
    for mode in ("high", "low"):
        comparison = build_example_5_comparison(mode)
        result = comparison.synthesize()
        text_path, image_path = export_comparison(
            comparison, output_directory, f"dirm_supervisory_example_5_aic_{mode}"
        )
        print(
            f"  AIC/BTS {mode}: states={len(comparison.graph)}, "
            f"initial_winning={result.initial_winning}, "
            f"AES states={len(result.winning)}, "
            f"initial_controls={len(result.policy.get(comparison.initial, ()))}\n"
            f"    graph: {image_path} ({text_path})"
        )


def example_6(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Run the equal-low-estimate, different-release-successor example."""
    _run_example(
        "Example 6 (high-level estimate counterexample)",
        build_example_6_bts,
        "dirm_supervisory_example_6",
        "example_6",
        output_directory,
    )


def example_user_provided(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Backward-compatible entry point for Example 1."""
    example_1(output_directory)


def example_framework_figure_2(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    """Backward-compatible entry point for Example 3."""
    example_3(output_directory)


def main() -> None:
    # This entry point exports files only; no interactive GUI backend is needed.
    import matplotlib
    matplotlib.use("Agg")
    output_directory = DEFAULT_OUTPUT_DIRECTORY
    print(f"Writing DIRM examples to {output_directory.resolve()}", flush=True)
    #
    # 这个注释别给我删了：
    # example 5用老的BTS是作为对照，说明老的BTS不可行，用TTS是为了在简单系统上验证可行性
    example_5(output_directory)
    #
    example_1(output_directory)
    #
    example_2(output_directory)
    #
    example_3(output_directory)
    #
    example_4(output_directory)
    #
    example_6(output_directory)


if __name__ == "__main__":
    main()

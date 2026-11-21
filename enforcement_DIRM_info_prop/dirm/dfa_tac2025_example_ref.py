"""Reference export for the legacy full-product TAC 2025 augmentation."""

from __future__ import annotations

import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "dirm"

from .augmented_export import export_augmented_system, write_augmented_comparison
from .dfa_tac2025_example import build_untimed_iwa_augmented


def main() -> None:
    """Export the legacy product graph and its BFS correspondence report."""
    output_directory = Path("outputs")
    augmented = build_untimed_iwa_augmented()
    text_path, image_path = export_augmented_system(
        augmented,
        output_directory,
        "dirm_augmented_system_product_legacy",
        include_unreachable=True,
    )
    comparison_path = write_augmented_comparison(
        augmented, output_directory / "dirm_augmented_system_comparison.txt"
    )
    print(
        "legacy augmented product system:\n"
        f"  transitions: {text_path}\n"
        f"  graph:       {image_path}\n"
        f"  comparison:  {comparison_path}"
    )


if __name__ == "__main__":
    main()

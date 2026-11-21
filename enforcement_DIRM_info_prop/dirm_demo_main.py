"""Export the DIRM observer for project Example 3."""

from pathlib import Path

from dirm import DIRMObserver
from dirm.export import export_observer
from dirm.paper_example import example_3_plant


def main() -> None:
    observer = DIRMObserver(
        example_3_plant(), observable={"a", "b"}, unobservable={"u"},
        releasable={"h"}, release_states={5, 9},
    )
    text_path, image_path = export_observer(
        observer, Path("outputs"), "dirm_example_3_observer"
    )
    print(f"observer graph: {image_path}")
    print(f"observer listing: {text_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from des_core.automata import DESExample
from des_core.deadlock import compute_deadlock_status
from des_core.visualization import (
    save_animation,
    save_belief_state_synthesis_final_png,
    save_observer_synthesis_animation,
    save_original_system_png,
)
from examples.non_deadlock import all_examples


def print_deadlock_summary(example: DESExample) -> None:
    dfa = example.dfa
    known_nodes = set(dfa.states)
    known_edges = {(source, target, event) for (source, event), target in dfa.transitions.items()}
    nondeadlock, deadlock = compute_deadlock_status(known_nodes, known_edges)

    print(f"\n[{example.name}]")
    print(example.description)
    print(f"initial state: {dfa.initial}")
    print(f"controllable events: {sorted(dfa.controllable)}")
    print(f"uncontrollable events: {sorted(dfa.uncontrollable)}")
    print(f"observable events: {sorted(dfa.observable)}")
    print(f"unobservable events: {sorted(dfa.unobservable)}")
    print(f"non-deadlock states: {sorted(nondeadlock)}")
    print(f"deadlock states: {sorted(deadlock)}")


def render_example(example: DESExample, output_dir: Path) -> None:
    example_dir = output_dir / example.name
    example_dir.mkdir(parents=True, exist_ok=True)
    plant_output = example_dir / "original.png"
    animation_output = example_dir / "synthesis.gif"
    observer_animation_output = example_dir / "belief_state_synthesis.gif"
    observer_final_output = example_dir / "belief_state_observer_final.png"
    original_dfa = example.original_dfa or example.dfa
    original_layout = example.original_layout or example.layout

    print_deadlock_summary(example)
    save_original_system_png(
        original_dfa,
        original_layout,
        plant_output,
        title=f"{example.name}: original DFA",
    )
    save_animation(example, animation_output)
    print(f"original system PNG written to: {plant_output.resolve()}")
    print(f"animation written to: {animation_output.resolve()}")
    if example.original_dfa is not None:
        save_observer_synthesis_animation(example, observer_animation_output)
        save_belief_state_synthesis_final_png(example, observer_final_output)
        print(f"belief-state animation written to: {observer_animation_output.resolve()}")
        print(f"belief-state final PNG written to: {observer_final_output.resolve()}")


def main() -> None:
    output_dir = Path("outputs")
    for example in all_examples():
        render_example(example, output_dir)


if __name__ == "__main__":
    main()

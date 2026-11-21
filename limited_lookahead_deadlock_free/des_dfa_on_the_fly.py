from __future__ import annotations

from collections import deque
from functools import cache
import json
import os
from pathlib import Path
import shutil
import stat
from time import perf_counter

import matplotlib

matplotlib.use("Agg")  # File-rendering runner; no interactive GUI is required.
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from des_core.automata import DESExample
from des_core.deadlock import BeliefStateSynthesisSnapshot, compute_deadlock_status
from des_core.limited_lookahead import post_leq
from des_core.ll_bts import (
    DecisionState,
    ObservationState,
    admissible_control_patterns,
    construct_ll_bts,
    controlled_unobservable_reach,
    decision_state_label,
    make_ll_bts_synthesis_snapshots,
    make_ll_bts_transition_report,
    observable_next,
    observation_state_label,
    _enabled_events,
    _decision_tag,
    _is_inconsistent_observation,
    _observation_tag,
    _pattern_label,
)
from des_core.visualization import (
    draw_belief_state_synthesis_snapshot,
    save_animation,
    save_original_system_png,
)
from examples.non_deadlock import all_examples


def print_deadlock_summary(example: DESExample) -> None:
    dfa = example.original_dfa or example.dfa
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
    print(f"lookahead limit: {example.lookahead_limit}")
    print(f"non-deadlock states: {sorted(nondeadlock)}")
    print(f"deadlock states: {sorted(deadlock)}")

    if example.original_dfa is not None:
        result = construct_ll_bts(dfa, dfa.initial, example.lookahead_limit)
        print(f"LL-BTS lookahead states: {sorted(result.lookahead_states)}")
        print(f"LL-BTS searched states Q_t: {sorted(result.searched_states)}")
        print(f"LL-BTS maximal good patterns: {[sorted(pattern) for pattern in result.maximal_good_patterns]}")


def render_example(example: DESExample, output_dir: Path) -> None:
    started_at = perf_counter()
    example_dir = output_dir / example.name
    example_dir.mkdir(parents=True, exist_ok=True)
    _clean_legacy_render_outputs(example_dir)
    generated: list[tuple[str, str]] = []
    plant_output = example_dir / "original.png"
    overall_connection_output = example_dir / "overall_connection.gif"
    ll_bts_output = example_dir / "ll_bts.gif"
    observer_final_output = example_dir / "ll_bts_final.png"
    transition_report_output = example_dir / "ll_bts_transition_report.txt"
    ll_bts_step_dir = example_dir / "ll_bts"
    original_dfa = example.original_dfa or example.dfa
    original_layout = example.original_layout or example.layout

    print_deadlock_summary(example)
    save_original_system_png(
        original_dfa,
        original_layout,
        plant_output,
        title=f"{example.name}: original DFA",
    )
    generated.append(("original.png", "原始 DFA 结构图。"))
    print(f"original system PNG written to: {plant_output.resolve()}")

    if example.original_dfa is None:
        save_animation(example, overall_connection_output)
        generated.append(("overall_connection.gif", "整体连接发现动画；最后一帧是整体连接发现完成后的固定点。"))
        print(f"overall connection animation written to: {overall_connection_output.resolve()}")
    elif example.name == "example3_possible_deadlock_full_partial_observation":
        online_dir = example_dir / "ll_bts_online_finals"
        snapshots = _make_physical_ll_bts_snapshots(example, example_dir)
        _write_ll_bts_step_outputs(example, ll_bts_step_dir, snapshots)
        _save_ll_bts_snapshots_gif(snapshots, ll_bts_output, example.name)
        _save_ll_bts_snapshot_png(snapshots[-1], observer_final_output, example.name)
        generated.append(("ll_bts.gif", "带分支选择记忆的单次物理 LL-BTS 执行动画。"))
        generated.append(("ll_bts_final.png", "本次物理 LL-BTS 执行路径的最终图。"))
        generated.append(("ll_bts/", "逐帧 LL-BTS 物理执行输出；每帧包含 PNG 和对应状态/转移 TXT。"))
        _write_case3_online_final_outputs(
            example.original_dfa,
            example.lookahead_limit,
            online_dir,
        )
        generated.append(("ll_bts_online_finals/", "case3 选定在线迭代 root 的完整 LL-BTS 终帧和 TXT 报告。"))
        print(f"LL-BTS online final frames written to: {online_dir.resolve()}")
    else:
        branch_count = _write_ll_bts_branch_outputs(example, ll_bts_step_dir)
        generated.append(("ll_bts/", f"LL-BTS 物理分支逐帧输出；每个 branch_XXX 是一个实际后继分支；branch count: {branch_count}."))
        transition_report_output.write_text(
            make_ll_bts_transition_report(
                example.original_dfa,
                example.lookahead_limit,
            ),
            encoding="utf-8",
        )
        generated.append(("ll_bts_transition_report.txt", "完整候选 LL-BTS 的选定阶段汇总报告，不代表单次物理执行路径。"))
        print(f"LL-BTS branch outputs written to: {ll_bts_step_dir.resolve()}")
        print(f"LL-BTS transition report written to: {transition_report_output.resolve()}")

    elapsed = perf_counter() - started_at
    description_output = example_dir / "文件说明+执行时间.txt"
    description_output.write_text(
        _run_description_text(example, elapsed, generated),
        encoding="utf-8",
    )
    print(f"file description written to: {description_output.resolve()}")


def _clean_legacy_render_outputs(example_dir: Path) -> None:
    for name in (
        "synthesis.gif",
        "ll_bts.gif",
        "ll_bts_final.png",
        "ll_bts_synthesis.gif",
        "ll_bts_chain.gif",
        "ll_bts_chain_final.png",
    ):
        path = example_dir / name

        if path.exists():
            path.unlink()

    for pattern in (
        "synthesis_frames*",
        "overall_connection_frames*",
        "ll_bts_synthesis_frames*",
        "ll_bts_frames*",
        "ll_bts_chain_frames*",
        "ll_bts_chain_instants",
        "ll_bts逐帧",
        "ll_bts",
    ):
        for path in example_dir.glob(pattern):
            if path.is_dir():
                _remove_tree(path)
            elif path.is_file():
                path.unlink()


def _remove_tree(path: Path) -> None:
    for child in path.rglob("*"):
        if child.is_file():
            os.chmod(child, 0o666)

    shutil.rmtree(path, onerror=_make_writable_and_retry)


def _make_writable_and_retry(func, path, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _write_ll_bts_step_outputs(
    example: DESExample,
    output_dir: Path,
    snapshots: list[BeliefStateSynthesisSnapshot],
) -> None:
    _clear_output_dir(output_dir)

    for index, snapshot in enumerate(snapshots):
        stem = f"frame_{index:03d}"
        _save_ll_bts_snapshot_png(snapshot, output_dir / f"{stem}.png", "LL-BTS")
        (output_dir / f"{stem}.txt").write_text(
            _ll_bts_snapshot_text(index, snapshot),
            encoding="utf-8",
        )

    (output_dir / "index.txt").write_text(
        "\n".join(
            [
                "LL-BTS 逐帧输出",
                f"example: {example.name}",
                f"lookahead limit u: {example.lookahead_limit}",
                f"frame count: {len(snapshots)}",
                "每个 frame_XXX.png 对应同名 frame_XXX.txt。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_ll_bts_branch_artifacts(
    example: DESExample,
    branch_dir: Path,
    snapshots: list[BeliefStateSynthesisSnapshot],
) -> None:
    """Write the frames, animation, and final image for one physical branch."""

    _write_ll_bts_step_outputs(example, branch_dir, snapshots)
    _save_ll_bts_snapshots_gif(snapshots, branch_dir / "ll_bts.gif", example.name)
    _save_ll_bts_snapshot_png(snapshots[-1], branch_dir / "ll_bts_final.png", example.name)


def _write_ll_bts_branch_outputs(example: DESExample, output_dir: Path) -> int:
    plant = example.original_dfa

    if plant is None:
        return 0

    # Physical branch-choice memory is deliberately outside the LL-BTS core.
    # It only selects which retained physical O->D successor is visualized on
    # repeated runs; Algorithm 1 construction and Algorithm 2 pruning do not
    # read or depend on this file. Keep it next to ll_bts/ so clearing rendered
    # branch folders does not erase the memory.
    memory_path = output_dir.parent / "物理分支选择记忆.json"
    branch_memory = _read_branch_memory(memory_path)

    _clear_output_dir(output_dir)
    horizon = example.lookahead_limit
    lookahead_states = post_leq(plant, frozenset({plant.initial}), horizon)
    initial: DecisionState = (plant.initial, frozenset({plant.initial}))
    initial_label = decision_state_label(plant, initial, lookahead_states)
    candidates = _initial_physical_successor_candidates(plant, horizon)

    if not candidates:
        snapshots = _physical_ll_bts_snapshots(plant, horizon, branch_memory)
        branch_dir = output_dir / "branch_001"
        _write_ll_bts_branch_artifacts(example, branch_dir, snapshots)
        (branch_dir / "branch_info.txt").write_text(
            "No initial physical successor candidate was available.\n",
            encoding="utf-8",
        )
        (output_dir / "index.txt").write_text(
            "\n".join(
                [
                    "LL-BTS branch outputs",
                    f"example: {example.name}",
                    f"initial decision: {initial_label}",
                    "branch count: 1",
                    "branch_001: no initial physical successor candidate",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        _write_branch_memory(memory_path, branch_memory)

        return 1

    index_lines = [
        "LL-BTS branch outputs",
        f"example: {example.name}",
        f"lookahead limit u: {horizon}",
        f"initial decision: {initial_label}",
        f"branch count: {len(candidates)}",
        "Each branch_XXX folder fixes one initial physical O -> D successor.",
    ]

    for index, (observation_label, successor_label, event, _successor) in enumerate(candidates, start=1):
        branch_name = f"branch_{index:03d}"
        branch_dir = output_dir / branch_name
        snapshots = _physical_ll_bts_snapshots(
            plant,
            horizon,
            branch_memory,
            forced_choices={initial_label: index - 1},
        )
        _write_ll_bts_branch_artifacts(example, branch_dir, snapshots)
        branch_info = "\n".join(
            [
                f"branch: {branch_name}",
                f"initial decision: {initial_label}",
                f"selected observation: {observation_label}",
                f"selected observable event: {event}",
                f"selected successor decision: {successor_label}",
                f"frame count: {len(snapshots)}",
                "Files: ll_bts.gif, ll_bts_final.png, frame_XXX.png, frame_XXX.txt, index.txt",
            ]
        )
        (branch_dir / "branch_info.txt").write_text(branch_info + "\n", encoding="utf-8")
        index_lines.append(
            f"{branch_name}: {observation_label} --{event}--> {successor_label}"
        )

    (output_dir / "index.txt").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    _write_branch_memory(memory_path, branch_memory)

    return len(candidates)


def _initial_physical_successor_candidates(
    plant,
    horizon: int,
) -> list[tuple[str, str, str, DecisionState]]:
    lookahead_states = post_leq(plant, frozenset({plant.initial}), horizon)
    patterns = admissible_control_patterns(plant)
    controllable_unobservable = plant.controllable & plant.unobservable
    enabled_observable_by_pattern = {
        pattern: frozenset((pattern | plant.uncontrollable) & plant.observable)
        for pattern in patterns
    }

    @cache
    def cached_ur(estimate, hidden_choice):
        return controlled_unobservable_reach(
            plant, estimate, hidden_choice, lookahead_states
        )

    @cache
    def cached_nx(estimate, event):
        return observable_next(plant, estimate, event, lookahead_states)

    initial: DecisionState = (plant.initial, frozenset({plant.initial}))
    candidates: list[tuple[str, str, str, DecisionState]] = []
    seen: set[tuple[str, str, str]] = set()

    for pattern in patterns:
        observation_estimate = cached_ur(
            initial[1], frozenset(pattern & controllable_unobservable)
        )
        observation: ObservationState = (observation_estimate, pattern)

        if _observation_tag(plant, observation, lookahead_states) == "N":
            continue

        if _is_inconsistent_observation(plant, observation):
            continue

        observation_label = observation_state_label(plant, observation, lookahead_states)

        for event in sorted(enabled_observable_by_pattern[pattern]):
            successor_estimate = cached_nx(observation_estimate, event)

            if not successor_estimate:
                continue

            for successor_root in sorted(successor_estimate):
                successor: DecisionState = (successor_root, successor_estimate)
                successor_label = decision_state_label(plant, successor, lookahead_states)
                key = (observation_label, successor_label, event)

                if key in seen:
                    continue

                seen.add(key)
                candidates.append((observation_label, successor_label, event, successor))

    return sorted(candidates, key=lambda item: (item[1], item[0], item[2]))


def _clear_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        _remove_tree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)


def _make_physical_ll_bts_snapshots(
    example: DESExample,
    example_dir: Path,
) -> list[BeliefStateSynthesisSnapshot]:
    plant = example.original_dfa

    if plant is None:
        return []

    memory_path = example_dir / "物理分支选择记忆.json"
    memory = _read_branch_memory(memory_path)
    snapshots = _physical_ll_bts_snapshots(plant, example.lookahead_limit, memory)
    _write_branch_memory(memory_path, memory)

    return snapshots


def _physical_ll_bts_snapshots(
    plant,
    horizon: int,
    branch_memory: dict[str, int],
    forced_choices: dict[str, int] | None=None,
) -> list[BeliefStateSynthesisSnapshot]:
    # A physical arrival starts a fresh online LL-BTS solve.  The previous
    # information estimate is not carried into the next solve: after arriving
    # physically at q, its initial decision state is D(q,{q}) and its local
    # window is x_L(q) = Post_{<u}({q}).
    patterns = admissible_control_patterns(plant)
    controllable_unobservable = plant.controllable & plant.unobservable
    enabled_observable_by_pattern = {
        pattern: frozenset((pattern | plant.uncontrollable) & plant.observable)
        for pattern in patterns
    }

    current_root: str | None = plant.initial
    visited_roots: set[str] = set()
    snapshots: list[BeliefStateSynthesisSnapshot] = []
    recent_stages: deque[tuple[frozenset[str], frozenset[tuple[str, str, str, str]]]] = deque(maxlen=2)
    all_nodes: set[str] = set()
    all_edges: set[tuple[str, str, str, str]] = set()

    def capture(
        title: str,
        current_decision: DecisionState | None,
        nodes: set[str],
        edges: set[tuple[str, str, str, str]],
        lookahead_states: frozenset[str],
    ) -> None:
        show_history = len(snapshots) < 5
        faded_nodes = (
            frozenset(
                node
                for previous_nodes, _previous_edges in recent_stages
                for node in previous_nodes
                if node not in nodes
            )
            if show_history
            else frozenset()
        )
        faded_edges = (
            frozenset(
                edge
                for _previous_nodes, previous_edges in recent_stages
                for edge in previous_edges
                if edge not in edges
            )
            if show_history
            else frozenset()
        )
        # Preserve the raw NX graph for display, but assess consistency only
        # after removing concrete bad nodes and their incident transitions.
        bad_nodes = {node for node in nodes
                     if _ll_bts_node_tag(plant, node, lookahead_states) == "N"}
        retained_edges = {edge for edge in edges
                          if edge[0] not in bad_nodes and edge[1] not in bad_nodes}
        inconsistent_nodes = _physical_inconsistent_nodes(
            plant, nodes - bad_nodes, retained_edges,
            lookahead_states=lookahead_states,
            expanded_decisions={
                decision_state_label(plant, (root, frozenset({root})), lookahead_states)
                for root in visited_roots
            },
        )
        snapshot = BeliefStateSynthesisSnapshot(
            title=title,
            known_nodes=frozenset(nodes),
            known_edges=frozenset(edges),
            current=(
                decision_state_label(plant, current_decision, lookahead_states)
                if current_decision is not None
                else None
            ),
            frontier=frozenset(),
            yes=frozenset(),
            no=frozenset(
                node
                for node in nodes
                if _ll_bts_node_tag(plant, node, lookahead_states) == "N"
            ),
            unknown=frozenset(
                node
                for node in nodes
                if node in inconsistent_nodes
                and _ll_bts_node_tag(plant, node, lookahead_states) != "N"
            ),
            closed_beliefs=frozenset(nodes),
            raw_beliefs=frozenset(),
            deadlock=frozenset(),
            layout_aliases=tuple(),
            faded_nodes=faded_nodes,
            faded_edges=faded_edges,
            layout_style="tree",
            label_style="compact",
        )
        snapshots.append(snapshot)
        recent_stages.append((frozenset(nodes), frozenset(edges)))

    initial_window = post_leq(plant, frozenset({plant.initial}), horizon)
    initial: DecisionState = (plant.initial, frozenset({plant.initial}))
    initial_label = decision_state_label(plant, initial, initial_window)
    capture(
        f"stage 0: initialize physical LL-BTS solve at q={plant.initial}; u={horizon}; |x_L|={len(initial_window)}",
        initial,
        {initial_label},
        set(),
        initial_window,
    )

    stage = 0
    last_window = initial_window

    while current_root is not None and current_root not in visited_roots:
        # Recompute x_L at every physical arrival, then reset the estimate to
        # the known physical state before constructing this round's LL-BTS.
        lookahead_states = post_leq(plant, frozenset({current_root}), horizon)
        last_window = lookahead_states
        current: DecisionState = (current_root, frozenset({current_root}))

        if _decision_tag(plant, current, lookahead_states) == "N":
            break

        visited_roots.add(current_root)
        decision_label = decision_state_label(plant, current, lookahead_states)
        nodes = {decision_label}
        edges: set[tuple[str, str, str, str]] = set()
        candidates: list[tuple[str, str, str, DecisionState]] = []
        observation_count = 0
        bad_observations = 0
        inconsistent_observations = 0

        for pattern in patterns:
            observation_estimate = controlled_unobservable_reach(
                plant, current[1], frozenset(pattern & controllable_unobservable),
                lookahead_states,
            )
            observation: ObservationState = (observation_estimate, pattern)
            observation_label = observation_state_label(plant, observation, lookahead_states)
            nodes.add(observation_label)
            observation_count += 1
            edges.add((decision_label, observation_label, _pattern_label(_enabled_events(plant, pattern)), "control"))

            is_bad = _observation_tag(plant, observation, lookahead_states) == "N"
            is_inconsistent = _is_inconsistent_observation(plant, observation)

            if is_bad:
                bad_observations += 1

            if is_inconsistent:
                inconsistent_observations += 1

            for event in sorted(enabled_observable_by_pattern[pattern]):
                successor_estimate = observable_next(
                    plant, observation_estimate, event, lookahead_states,
                )

                if not successor_estimate:
                    continue

                for successor_root in sorted(successor_estimate):
                    successor: DecisionState = (successor_root, successor_estimate)
                    successor_label = decision_state_label(plant, successor, lookahead_states)
                    nodes.add(successor_label)
                    edges.add((observation_label, successor_label, event, "observable"))

                    if (not is_bad and not is_inconsistent
                            and _decision_tag(plant, successor, lookahead_states) != "N"):
                        candidates.append((observation_label, successor_label, event, successor))

        selected = _choose_physical_successor(
            decision_label,
            candidates,
            branch_memory,
            forced_choices,
        )
        selected_label = "<none>"

        if selected is not None:
            observation_label, successor_label, event, successor = selected
            edges.add((observation_label, successor_label, event, "observable"))
            nodes.add(successor_label)
            selected_label = successor_label
            # The O -> D edge retains its information estimate for this round,
            # while the next physical solve restarts from the selected actual
            # root with singleton estimate {root}.
            current_root = successor[0]
        else:
            current_root = None

        all_nodes.update(nodes)
        all_edges.update(edges)
        stage += 1
        capture(
            (
                f"stage {stage}: solve from physical q={current[0]}; {decision_label}; "
                f"u={horizon}; |x_L|={len(lookahead_states)}; observations={observation_count}, "
                f"physical successor candidates={len(candidates)}, selected={selected_label}, "
                f"bad observations={bad_observations}, "
                f"inconsistent observations={inconsistent_observations}"
            ),
            ((current_root, frozenset({current_root})) if current_root is not None else None),
            nodes,
            edges,
            lookahead_states,
        )

    if all_nodes:
        capture(
            f"stage {stage + 1}: complete physical LL-BTS run",
            None,
            all_nodes,
            all_edges,
            last_window,
        )

    return snapshots


def _choose_physical_successor(
    decision_label: str,
    candidates: list[tuple[str, str, str, DecisionState]],
    branch_memory: dict[str, int],
    forced_choices: dict[str, int] | None=None,
) -> tuple[str, str, str, DecisionState] | None:
    if not candidates:
        return None

    ordered = sorted(candidates, key=lambda item: (item[1], item[0], item[2]))

    if forced_choices is not None and decision_label in forced_choices:
        index = forced_choices[decision_label] % len(ordered)

        return ordered[index]

    index = branch_memory.get(decision_label, 0) % len(ordered)
    branch_memory[decision_label] = branch_memory.get(decision_label, 0) + 1

    return ordered[index]


def _read_branch_memory(memory_path: Path) -> dict[str, int]:
    if not memory_path.exists():
        return {}

    try:
        data = json.loads(memory_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}

    if not isinstance(data, dict):
        return {}

    memory: dict[str, int] = {}

    for key, value in data.items():
        try:
            memory[str(key)] = int(value)
        except (TypeError, ValueError):
            continue

    return memory


def _write_branch_memory(memory_path: Path, memory: dict[str, int]) -> None:
    memory_path.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ll_bts_node_tag(plant, node: str, lookahead_states: frozenset[str]) -> str:
    if node.startswith("D(") and node.endswith(")"):
        body = node[2:-1]
        root, estimate_text = body.split(",", 1)

        return _decision_tag(plant, (root, _parse_state_set(estimate_text)), lookahead_states)

    if node.startswith("O(") and node.endswith(")"):
        body = node[2:-1]

        if "},{" not in body:
            return "U"

        estimate_text, pattern_text = body.split("},{", 1)
        observation = (
            _parse_state_set(f"{estimate_text}}}"),
            _parse_state_set(f"{{{pattern_text}"),
        )
        tag = _observation_tag(plant, observation, lookahead_states)

        # Concrete deadlocks also satisfy the inconsistency predicate, but
        # must retain the bad-state classification used during synthesis.
        if tag == "N":
            return tag

        if _is_inconsistent_observation(plant, observation):
            return "I"

        return tag

    return "U"


def _physical_inconsistent_nodes(plant, nodes, edges, *, lookahead_states,
                                 expanded_decisions=None) -> set[str]:
    """Apply the O-completeness and D-choice consistency definitions.

    O requires all permitted observable NX successors *inside x_L* to be
    represented. D requires at least one retained D -> O choice. A locally
    disabled plant transition alone is neither kind of inconsistency.
    """

    control_sources = {source for source, _target, _event, kind in edges if kind == "control"}
    represented = {(source, event) for source, _target, event, kind in edges if kind == "observable"}
    inconsistent: set[str] = set()

    for node in nodes:
        if node.startswith("D("):
            if (expanded_decisions is None or node in expanded_decisions) and node not in control_sources:
                inconsistent.add(node)

            continue

        if not node.startswith("O(") or "},{" not in node:
            continue

        body = node[2:-1]
        estimate_text, pattern_text = body.split("},{", 1)
        estimate = _parse_state_set(f"{estimate_text}}}")
        pattern = _parse_state_set(f"{{{pattern_text}")
        required = {
            event
            for state in estimate
            for event, target in plant.enabled(state)
            if (event in _enabled_events(plant, pattern)
                and event in plant.observable and target in lookahead_states)
        }

        if not required.issubset({event for source, event in represented if source == node}):
            inconsistent.add(node)

    return inconsistent


def _parse_state_set(text: str) -> frozenset[str]:
    if text == "{}":
        return frozenset()

    return frozenset(item for item in text[1:-1].split(",") if item)


def _save_ll_bts_snapshots_gif(
    snapshots: list[BeliefStateSynthesisSnapshot],
    output: Path,
    title_prefix: str,
) -> None:
    if not snapshots:
        return

    fig, ax = plt.subplots(figsize=(22, 12))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.08)

    def update(frame: int) -> None:
        draw_belief_state_synthesis_snapshot(ax, snapshots[frame], {}, title_prefix)

    animation = FuncAnimation(fig, update, frames=len(snapshots), interval=1200, repeat=True)
    animation.save(output, writer=PillowWriter(fps=1))
    plt.close(fig)


def _write_case3_online_final_outputs(plant, horizon: int, output_dir: Path) -> None:
    _clear_output_dir(output_dir)

    roots = _case3_online_roots()
    index_lines = [
        "Case 3 online LL-BTS final frames",
        f"initial: {plant.initial}",
        f"lookahead limit u: {horizon}",
        "Each PNG is the completed LL-BTS for one online iteration root.",
        "",
    ]

    for index, root in enumerate(roots):
        result = construct_ll_bts(plant, root, horizon)
        snapshot = _ll_bts_result_snapshot(plant, root, horizon, result, index)
        png_name = f"iteration_{index:04d}.png"
        txt_name = f"iteration_{index:04d}.txt"
        _save_ll_bts_snapshot_png(snapshot, output_dir / png_name, "case3 online LL-BTS")
        (output_dir / txt_name).write_text(
            _case3_online_final_text(index, root, result, snapshot),
            encoding="utf-8",
        )
        index_lines.append(f"{png_name} / {txt_name}: root={root}; {snapshot.title}")

    (output_dir / "index.txt").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def _case3_online_roots() -> tuple[str, ...]:
    return ("q_2", "q_0", "q_4", "q_15", "q_16", "q_17", "q_3", "q_9")


def _ll_bts_result_snapshot(plant, root, horizon: int, result, index: int) -> BeliefStateSynthesisSnapshot:
    decision_labels = {
        decision_state_label(plant, state, result.lookahead_states)
        for state in result.decision_states
    }
    observation_labels = {
        observation_state_label(plant, state, result.lookahead_states)
        for state in result.observation_states
    }
    no_nodes = {
        decision_state_label(plant, state, result.lookahead_states)
        for state in result.decision_states
        if _decision_tag(plant, state, result.lookahead_states) == "N"
    }
    no_nodes.update(
        observation_state_label(plant, state, result.lookahead_states)
        for state in result.observation_states
        if _observation_tag(plant, state, result.lookahead_states) == "N"
    )
    unknown_nodes = {
        observation_state_label(plant, state, result.lookahead_states)
        for state in result.observation_states
        if _is_inconsistent_observation(plant, state)
    }
    nodes = decision_labels | observation_labels | {
        node
        for source, target, _event, _kind in result.edges
        for node in (source, target)
    }
    initial = (root, frozenset({root}))
    current = decision_state_label(plant, initial, result.lookahead_states)

    return BeliefStateSynthesisSnapshot(
        title=(
            f"online iteration {index}: completed LL-BTS; root={root}; "
            f"u={horizon}; |D|={len(result.decision_states)}, |O|={len(result.observation_states)}"
        ),
        known_nodes=frozenset(nodes),
        known_edges=result.edges,
        current=current,
        frontier=frozenset(),
        yes=frozenset(),
        no=frozenset(nodes & no_nodes),
        unknown=frozenset(nodes & unknown_nodes),
        closed_beliefs=frozenset(nodes),
        raw_beliefs=frozenset(),
        deadlock=frozenset(),
        layout_aliases=tuple(),
        layout_style="chain",
        label_style="compact",
    )


def _save_ll_bts_snapshot_png(snapshot: BeliefStateSynthesisSnapshot, output: Path, title_prefix: str) -> None:
    fig, ax = plt.subplots(figsize=(22, 12))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.08)
    draw_belief_state_synthesis_snapshot(ax, snapshot, {}, title_prefix)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def _case3_online_final_text(index: int, root: str, result, snapshot: BeliefStateSynthesisSnapshot) -> str:
    nodes = sorted(snapshot.known_nodes)
    decisions = [node for node in nodes if node.startswith("D(")]
    observations = [node for node in nodes if node.startswith("O(")]
    control_edges = sorted(edge for edge in snapshot.known_edges if edge[3] == "control")
    observable_edges = sorted(edge for edge in snapshot.known_edges if edge[3] == "observable")

    lines = [
        f"Case 3 online LL-BTS final frame {index}",
        snapshot.title,
        "",
        f"root: {root}",
        f"lookahead states ({len(result.lookahead_states)}): {', '.join(sorted(result.lookahead_states))}",
        f"searched concrete states Q_t ({len(result.searched_states)}): {', '.join(sorted(result.searched_states))}",
        f"maximal good patterns: {_patterns_text(result.maximal_good_patterns)}",
        "",
        f"current decision: {snapshot.current or '<none>'}",
        "",
        f"decision states ({len(decisions)}):",
        *(f"  {node}" for node in decisions),
        "",
        f"observation states ({len(observations)}):",
        *(f"  {node}" for node in observations),
        "",
        f"decision-to-observation transitions ({len(control_edges)}):",
        *(f"  {source} --{_display_control_pattern(event)}--> {target}" for source, target, event, _kind in control_edges),
        "",
        f"observation-to-decision transitions ({len(observable_edges)}):",
        *(f"  {source} --{event}--> {target}" for source, target, event, _kind in observable_edges),
        "",
        "frontier:",
        *(f"  {node}" for node in sorted(snapshot.frontier)),
    ]

    if not snapshot.frontier:
        lines.append("  <empty>")

    return "\n".join(lines) + "\n"


def _ll_bts_snapshot_text(index: int, snapshot: BeliefStateSynthesisSnapshot) -> str:
    nodes = sorted(snapshot.known_nodes)
    decisions = [node for node in nodes if node.startswith("D(")]
    observations = [node for node in nodes if node.startswith("O(")]
    other_nodes = [node for node in nodes if not node.startswith(("D(", "O("))]
    emptyset_observations = [node for node in observations if node.endswith(",{})")]
    control_edges = sorted(edge for edge in snapshot.known_edges if edge[3] == "control")
    observable_edges = sorted(edge for edge in snapshot.known_edges if edge[3] == "observable")
    faded_edges = sorted(snapshot.faded_edges)

    lines = [
        f"LL-BTS frame {index:04d}",
        snapshot.title,
        "",
        f"current: {snapshot.current or '<none>'}",
        f"frontier: {', '.join(sorted(snapshot.frontier)) if snapshot.frontier else '<empty>'}",
        f"bad states: {', '.join(sorted(snapshot.no)) if snapshot.no else '<empty>'}",
        (
            "unknown/inconsistent states: "
            f"{', '.join(sorted(snapshot.unknown)) if snapshot.unknown else '<empty>'}"
        ),
        "",
        f"decision states ({len(decisions)}):",
        *(f"  {node}" for node in decisions),
        "",
        f"observation states ({len(observations)}):",
        *(f"  {node}" for node in observations),
        "",
        f"emptyset control observation states ({len(emptyset_observations)}):",
        *(f"  {node}" for node in emptyset_observations),
    ]

    if other_nodes:
        lines.extend(["", f"other states ({len(other_nodes)}):", *(f"  {node}" for node in other_nodes)])

    lines.extend(
        [
            "",
            f"decision-to-observation transitions ({len(control_edges)}):",
            *(f"  {source} --{_display_control_pattern(event)}--> {target}" for source, target, event, _kind in control_edges),
            "",
            f"observation-to-decision transitions ({len(observable_edges)}):",
            *(f"  {source} --{event}--> {target}" for source, target, event, _kind in observable_edges),
        ]
    )

    if faded_edges:
        lines.extend(
            [
                "",
                f"faded historical transitions ({len(faded_edges)}):",
                *(f"  {source} --{_display_control_pattern(event)}--> {target} [{kind}]" for source, target, event, kind in faded_edges),
            ]
        )

    return "\n".join(lines) + "\n"


def _display_control_pattern(pattern: str) -> str:
    if pattern == "{}":
        return "emptyset ({})"

    return pattern


def _run_description_text(
    example: DESExample,
    elapsed_seconds: float,
    generated: list[tuple[str, str]],
) -> str:
    lines = [
        "文件说明+执行时间",
        "",
        f"例子: {example.name}",
        f"执行时间: {elapsed_seconds:.2f} 秒",
        "",
        "本次生成或更新的内容:",
    ]

    for path, description in generated:
        lines.append(f"- {path}: {description}")

    lines.extend(
        [
            "",
            "命名说明:",
            "- overall_connection.gif: 整体 plant/observer 连接发现过程，不是 LL-BTS。",
            "- ll_bts/: LL-BTS 物理分支输出目录；index.txt 汇总每个分支选择的初始 O -> D 后继。",
            "- ll_bts/branch_XXX/: 一个实际物理分支；包含 ll_bts.gif、ll_bts_final.png、frame_XXX.png 和同名 TXT。",
        ]
    )

    return "\n".join(lines) + "\n"


def _patterns_text(patterns) -> str:
    if not patterns:
        return "<none>"

    return ", ".join("{" + ",".join(sorted(pattern)) + "}" for pattern in patterns)


def _example_by_name(name: str) -> DESExample:
    examples = {example.name: example for example in all_examples()}

    try:
        return examples[name]
    except KeyError as exc:
        available = ", ".join(sorted(examples))

        raise ValueError(f"unknown example {name!r}; available examples: {available}") from exc


def _render_named_example(name: str) -> None:
    output_dir = Path("outputs")
    render_example(_example_by_name(name), output_dir)


def main_example1_full() -> None:
    _render_named_example("example1_symbolic_cycles_full")


def main_example1_partial() -> None:
    _render_named_example("example1_symbolic_cycles_full_partial_observation")


def main_example2_partial() -> None:
    _render_named_example("example2_nested_cycles_deadlock_full_partial_observation")


def main_example3_full() -> None:
    _render_named_example("example3_possible_deadlock_full")


def main_example3_partial() -> None:
    _render_named_example("example3_possible_deadlock_full_partial_observation")


def main() -> None:
    # New default: draft-aligned offline scan followed by certified LL-BTS.
    # Historical figure entry points above remain available for reproduction.
    from certified_benchmark import main as certified_main

    certified_main()


if __name__ == "__main__":
    main()

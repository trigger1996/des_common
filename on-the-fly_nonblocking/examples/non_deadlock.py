from __future__ import annotations

from des_core.automata import DESExample, DFA
from des_core.observer import build_partial_observation_example


def build_small_cycle_example() -> DESExample:
    states = frozenset({"q_0", "q_1", "q_2", "q_3", "q_4"})
    controllable = frozenset({"a", "b", "d", "e"})
    uncontrollable = frozenset({"c", "f"})
    transitions = {
        ("q_0", "a"): "q_1",
        ("q_1", "b"): "q_2",
        ("q_2", "c"): "q_0",
        ("q_1", "d"): "q_3",
        ("q_3", "e"): "q_4",
        ("q_4", "f"): "q_1",
    }
    dfa = DFA(
        states=states,
        initial="q_0",
        events=controllable | uncontrollable,
        controllable=controllable,
        observable=controllable | uncontrollable,
        transitions=transitions,
    )
    layout = {
        "q_0": (0.0, 0.0),
        "q_1": (2.2, 0.0),
        "q_2": (4.4, 0.0),
        "q_3": (2.2, -2.0),
        "q_4": (4.4, -2.0),
    }
    return DESExample(
        name="example1_symbolic_cycles_full",
        dfa=dfa,
        layout=layout,
        description="Symbolic full-observation DFA. All states are non-deadlock and two cycles share q_1.",
    )


def build_nested_cycle_deadlock_example() -> DESExample:
    states = frozenset(f"q_{index}" for index in range(13))
    controllable = frozenset({"a", "b", "c", "e", "f", "h", "i", "k", "m", "o"})
    uncontrollable = frozenset({"d", "g", "j", "l", "n"})
    transitions = {
        ("q_0", "a"): "q_1",
        ("q_1", "b"): "q_2",
        ("q_2", "c"): "q_3",
        ("q_3", "d"): "q_1",
        ("q_2", "e"): "q_4",
        ("q_4", "f"): "q_5",
        ("q_5", "g"): "q_2",
        ("q_3", "h"): "q_6",
        ("q_6", "i"): "q_7",
        ("q_7", "j"): "q_6",
        ("q_5", "k"): "q_8",
        ("q_8", "l"): "q_9",
        ("q_9", "m"): "q_10",
        ("q_10", "n"): "q_8",
        ("q_7", "o"): "q_11",
        ("q_11", "a"): "q_12",
        ("q_10", "b"): "q_6",
    }
    dfa = DFA(
        states=states,
        initial="q_0",
        events=controllable | uncontrollable,
        controllable=controllable,
        observable=controllable | uncontrollable,
        transitions=transitions,
    )
    layout = {
        "q_0": (0.0, 0.0),
        "q_1": (2.0, 0.0),
        "q_2": (4.0, 0.0),
        "q_3": (6.0, 0.0),
        "q_4": (4.0, -1.8),
        "q_5": (6.0, -1.8),
        "q_6": (8.0, -0.8),
        "q_7": (10.0, -0.8),
        "q_8": (6.0, -3.6),
        "q_9": (8.0, -3.6),
        "q_10": (10.0, -3.6),
        "q_11": (12.0, -0.8),
        "q_12": (14.0, -0.8),
    }
    return DESExample(
        name="example2_nested_cycles_deadlock_full",
        dfa=dfa,
        layout=layout,
        description=(
            "Complex symbolic DFA with singleton deadlock q_12, an outer cycle "
            "q_1-q_2-q_3, a nested cycle q_2-q_4-q_5, and deeper cycles q_6-q_7 "
            "and q_8-q_9-q_10."
        ),
    )


def build_possible_deadlock_partial_observation_example() -> DESExample:
    states = frozenset(f"q_{index}" for index in range(15))
    controllable = frozenset({"a", "b", "c", "d", "e", "f", "g", "h", "i", "k", "l", "m"})
    uncontrollable = frozenset({"u", "v", "w", "x", "y", "z"})
    transitions = {
        ("q_0", "a"): "q_1",
        ("q_0", "u"): "q_4",

        # Observable outer cycle with an observable nested cycle through q_2.
        ("q_1", "b"): "q_2",
        ("q_2", "c"): "q_3",
        ("q_3", "d"): "q_1",
        ("q_2", "e"): "q_6",
        ("q_6", "f"): "q_2",

        # Standalone concrete deadlock reached by an observable event.
        ("q_3", "g"): "q_9",

        # Fully observable livelock: the plant can stay forever on observable h.
        ("q_6", "i"): "q_11",
        ("q_11", "h"): "q_11",
        ("q_11", "z"): "q_2",

        # Observable entry to a branch whose unobservable reach contains livelock.
        ("q_2", "k"): "q_7",

        # Unobservable reach from q_0 contains an unobservable cycle and a deadlock.
        ("q_4", "v"): "q_5",
        ("q_5", "u"): "q_4",
        ("q_5", "m"): "q_0",
        ("q_5", "w"): "q_10",

        # Unobservable livelock inside the reach of q_7.
        ("q_7", "x"): "q_8",
        ("q_8", "y"): "q_12",
        ("q_12", "l"): "q_8",
        ("q_12", "z"): "q_13",
        ("q_13", "y"): "q_12",

        # Exit from the hidden livelock region back to an observable path.
        ("q_13", "b"): "q_14",
        ("q_14", "c"): "q_3",
    }
    dfa = DFA(
        states=states,
        initial="q_0",
        events=controllable | uncontrollable,
        controllable=controllable,
        observable=controllable | uncontrollable,
        transitions=transitions,
    )
    layout = {
        "q_0": (0.0, 0.0),
        "q_1": (2.0, 0.0),
        "q_2": (4.0, 0.0),
        "q_3": (6.0, 0.0),
        "q_4": (0.0, -2.0),
        "q_5": (2.0, -2.0),
        "q_6": (4.0, -2.0),
        "q_7": (4.0, -4.0),
        "q_8": (6.0, -4.0),
        "q_9": (8.0, 0.0),
        "q_10": (2.0, -4.0),
        "q_11": (6.0, -2.0),
        "q_12": (8.0, -4.0),
        "q_13": (10.0, -4.0),
        "q_14": (10.0, -2.0),
    }
    return DESExample(
        name="example3_possible_deadlock_full",
        dfa=dfa,
        layout=layout,
        description=(
            "Complex partial-observation risk DFA with an unobservable cycle, "
            "nested observable cycles, an observable deadlock q_9, a hidden "
            "deadlock q_10 inside unobservable reach, a fully observable livelock "
            "q_11, and an unobservable-reach livelock q_12-q_13."
        ),
    )


def all_examples() -> list[DESExample]:
    example1 = build_small_cycle_example()
    example2 = build_nested_cycle_deadlock_example()
    example3 = build_possible_deadlock_partial_observation_example()

    example1_partial = build_partial_observation_example(
        example1,
        observable=frozenset({"a", "b", "d", "e"}),
    )
    example2_partial = build_partial_observation_example(
        example2,
        observable=frozenset({"a", "b", "c", "e", "h", "k", "m", "o"}),
    )
    example3_partial = build_partial_observation_example(
        example3,
        observable=frozenset({"a", "b", "c", "d", "e", "f", "g", "h", "i", "k", "l", "u"}),
    )
    return [example1, example1_partial, example2, example2_partial, example3, example3_partial]

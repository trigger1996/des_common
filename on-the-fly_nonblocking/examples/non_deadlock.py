from __future__ import annotations

from des_core.automata import DESExample, DFA
from des_core.observer import build_partial_observation_example


# Frame alignment notes for rendered outputs:
#
# - Full-observation examples only use overall_connection.gif. In that animation,
#   frame_0000 is the initial known state, each intermediate frame records one
#   discovered transition, and the final frame is the fixed point. These frames
#   are not Algorithm 1 while-loop iterations.
#
# - Partial-observation examples use ll_bts.gif for the current
#   limited-lookahead information-state construction.


def build_small_cycle_example() -> DESExample:
    # example1_symbolic_cycles_full:
    #   overall_connection.gif has 8 frames:
    #   0000 initial, 0001-0006 discovered transitions, 0007 fixed point.
    # example1_symbolic_cycles_full_partial_observation:
    #   overall_connection.gif has 9 frames:
    #   0000 initial, 0001-0007 discovered transitions, 0008 fixed point.
    #   ll_bts.gif uses the local lookahead limit configured below.
    states = frozenset({"q_0", "q_1", "q_2", "q_3", "q_4"})
    controllable = frozenset({"a", "b", "u"})
    uncontrollable = frozenset()
    transitions = {
        ("q_0", "a"): "q_1",
        ("q_1", "a"): "q_2",
        ("q_2", "u"): "q_0",
        ("q_1", "b"): "q_3",
        ("q_3", "a"): "q_4",
        ("q_4", "u"): "q_1",
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
        lookahead_limit=2,
    )


def build_nested_cycle_deadlock_example() -> DESExample:
    # example2_nested_cycles_deadlock_full_partial_observation:
    #   This case is used only through its partial-observation version.
    #   Event o is the only observable event; a, b, and u are hidden.
    states = frozenset(f"q_{index}" for index in range(14))
    controllable = frozenset({"a", "b", "o"})
    uncontrollable = frozenset({"u"})
    transitions = {
        ("q_0", "a"): "q_1",
        ("q_1", "a"): "q_2",
        ("q_2", "a"): "q_3",
        ("q_3", "u"): "q_1",
        ("q_2", "b"): "q_4",
        ("q_4", "a"): "q_5",
        ("q_5", "u"): "q_2",
        ("q_3", "o"): "q_6",
        ("q_6", "a"): "q_7",
        ("q_7", "u"): "q_6",
        # q_4 and q_5 can appear in the same unobservable tail. The same
        # observation o sends them to q_8 and q_11, whose hidden reaches merge.
        ("q_4", "o"): "q_8",
        ("q_5", "o"): "q_11",
        ("q_8", "u"): "q_9",
        ("q_9", "a"): "q_10",
        ("q_10", "u"): "q_8",
        ("q_8", "b"): "q_11",
        ("q_11", "u"): "q_8",
        ("q_7", "b"): "q_12",
        ("q_10", "b"): "q_13",
        ("q_11", "o"): "q_6",
        ("q_10", "o"): "q_6",
    }
    dfa = DFA(
        states=states,
        initial="q_0",
        events=controllable | uncontrollable,
        controllable=controllable,
        observable=frozenset({"o"}),
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
        "q_13": (12.0, -3.6),
    }
    return DESExample(
        name="example2_nested_cycles_deadlock_full",
        dfa=dfa,
        layout=layout,
        description=(
            "Complex symbolic DFA with deadlocks q_12 and q_13, an outer cycle "
            "q_1-q_2-q_3, a nested cycle q_2-q_4-q_5, and deeper cycles q_6-q_7 "
            "and q_8-q_9-q_10. Under partial observation, q_4 and q_5 may share "
            "one unobservable tail; the same observable event o reaches q_8 and "
            "q_11, whose unobservable reaches merge."
        ),
        lookahead_limit=6,
    )


def build_possible_deadlock_partial_observation_example() -> DESExample:
    # example3_possible_deadlock_full:
    #   overall_connection.gif has 25 frames:
    #   0000 initial, 0001-0023 discovered transitions, 0024 fixed point.
    # example3_possible_deadlock_full_partial_observation:
    #   overall_connection.gif has 52 frames:
    #   0000 initial, 0001-0050 discovered transitions, 0051 fixed point.
    #   ll_bts.gif uses the local lookahead limit configured below.
    #   Paper-selected frames 0003, 0009, 0013, and 0016 correspond to
    #   Algorithm 1 loops 3, 9, 13, and 16, respectively.
    #   Pruning is applied immediately after the yielded snapshot, so a
    #   prunable node may be removed in the next frame rather than being shown
    #   as N in one selected frame and deleted in the next selected frame.
    states = frozenset(f"q_{index}" for index in range(14)) | frozenset({"q_15", "q_16", "q_17"})
    controllable = frozenset({"a", "c", "u"})
    uncontrollable = frozenset({"b", "v"})
    transitions = {
        ("q_0", "a"): "q_1",
        ("q_0", "b"): "q_4",

        # The plant starts from q_2. Under partial observation, q_2 and q_1
        # are connected by hidden events before a visible return to q_0.
        ("q_2", "u"): "q_1",
        ("q_1", "u"): "q_2",
        ("q_1", "b"): "q_0",

        # Observable outer cycle with an observable nested cycle through q_2.
        ("q_1", "a"): "q_2",
        ("q_2", "a"): "q_3",
        ("q_3", "a"): "q_1",
        ("q_2", "b"): "q_6",
        ("q_6", "a"): "q_2",

        # Standalone concrete deadlock reached by an observable event.
        ("q_3", "b"): "q_9",

        # Fully observable livelock: the plant can stay forever on observable h.
        ("q_6", "b"): "q_11",
        ("q_11", "a"): "q_11",
        ("q_11", "u"): "q_2",

        # Observable entry to a branch whose unobservable reach contains livelock.
        ("q_2", "c"): "q_7",

        # Unobservable reach from q_0 contains an unobservable cycle and a deadlock.
        ("q_4", "u"): "q_5",
        ("q_5", "a"): "q_4",
        ("q_5", "u"): "q_0",
        ("q_5", "v"): "q_10",

        # Same observation from two states in one unobservable tail. After
        # observing c, q_4 and q_5 may move to q_15 and q_16, respectively;
        # both targets reach the same unobservable tail in one hidden step.
        ("q_4", "c"): "q_15",
        ("q_5", "c"): "q_16",
        ("q_15", "u"): "q_17",
        ("q_16", "u"): "q_17",
        ("q_17", "a"): "q_3",

        # Unobservable reach inside q_7's branch. q_13 is a hidden deadlock.
        ("q_7", "u"): "q_8",
        ("q_8", "u"): "q_12",
        ("q_12", "a"): "q_8",
        ("q_12", "u"): "q_13",

        # Hidden deadlock continuation from q_10 to q_13.
        ("q_10", "v"): "q_13",
    }
    dfa = DFA(
        states=states,
        initial="q_2",
        events=controllable | uncontrollable,
        controllable=controllable,
        observable=controllable | uncontrollable,
        transitions=transitions,
    )
    layout = {
        "q_2": (0.0, 0.0),
        "q_1": (2.0, 0.0),
        "q_0": (4.0, 0.0),
        "q_3": (6.0, 0.0),
        "q_4": (6.0, -2.0),
        "q_5": (8.0, -2.0),
        "q_6": (2.0, -2.0),
        "q_7": (4.0, -4.0),
        "q_8": (6.0, -4.0),
        "q_9": (8.0, 0.0),
        "q_10": (10.0, -2.0),
        "q_11": (4.0, -2.0),
        "q_12": (8.0, -4.0),
        "q_13": (10.0, -4.0),
        "q_15": (6.0, -6.0),
        "q_16": (8.0, -6.0),
        "q_17": (10.0, -6.0),
    }
    return DESExample(
        name="example3_possible_deadlock_full",
        dfa=dfa,
        layout=layout,
        description=(
            "Complex partial-observation risk DFA with an unobservable cycle, "
            "initial hidden ambiguity between q_2 and q_1, "
            "nested observable cycles, an observable deadlock q_9, a hidden "
            "deadlock q_10 inside unobservable reach, a fully observable livelock "
            "q_11, a hidden deadlock q_13 in the q_7 reach, and two states "
            "in one unobservable tail that share the same observation before "
            "merging into a common hidden reach."
        ),
        lookahead_limit=4,
    )


def all_examples() -> list[DESExample]:
    example1 = build_small_cycle_example()
    example2 = build_nested_cycle_deadlock_example()
    example3 = build_possible_deadlock_partial_observation_example()

    example1_partial = build_partial_observation_example(
        example1,
        observable=frozenset({"a", "b"}),
    )
    example2_partial = build_partial_observation_example(
        example2,
        observable=frozenset({"o"}),
    )
    example3_partial = build_partial_observation_example(
        example3,
        observable=frozenset({"a", "b", "c"}),
    )
    return [example1, example1_partial, example2_partial, example3, example3_partial]

"""Independent project examples used by the DIRM observer and supervisor."""

from .dfa import DFA


def example_3_plant() -> DFA:
    """Return project Example 3."""
    return DFA.build(
        states=set(range(10)),
        alphabet={"a", "b", "h", "u"},
        initial=0,
        transitions={
            # left branch
            (0, "h"): 2,
            (0, "b"): 8,
            (2, "h"): 4,
            (4, "a"): 6,
            (6, "u"): 8,
            (8, "u"): 9,

            # right branch
            (0, "u"): 1,
            (1, "b"): 3,
            (1, "h"): 3,
            (3, "u"): 5,
            (5, "a"): 7,

            (9, "a"): 3,
            (9, "b"): 9,
        },
        secret_states={7},
    )


def build_example_3_bts():
    """Build project Example 3.

    Event ``a`` is controllable; ``b``, the unobservable event ``u``, and
    the releasable event ``h`` are uncontrollable. Release states 5 and 9
    remain separated along the plant's right and bottom branches.
    """
    from .supervisory import SupervisoryDIRMBTS

    bts = SupervisoryDIRMBTS(
        example_3_plant(),
        controllable={"a"},
        uncontrollable={"b", "h", "u"},
        observable={"a", "b"},
        unobservable={"u"},
        releasable={"h"},
        release_states={5, 9},
    )
    bts.construct()
    return bts


def example_4_plant() -> DFA:
    """Return the independent seven-state plant used as project Example 4."""
    return DFA.build(
        states=set(range(7)),
        alphabet={"a", "h", "u"},
        initial=0,
        transitions={
            (0, "h"): 1,
            (0, "u"): 2,
            (1, "u"): 3,
            (2, "a"): 4,
            (3, "h"): 5,
            (6, "a"): 3,
            (4, "u"): 6,
            (5, "u"): 6,
            (6, "u"): 6,
        },
        secret_states={5},
    )


def build_example_4_bts():
    """Build the supervisory DIRM system for project Example 4."""
    from .supervisory import SupervisoryDIRMBTS

    bts = SupervisoryDIRMBTS(
        example_4_plant(),
        controllable={"a"},
        uncontrollable={"h", "u"},
        observable={"a"},
        unobservable={"u"},
        releasable={"h"},
        release_states={3, 6},
    )
    bts.construct()
    return bts


def example_5_plant() -> DFA:
    """DIRM Fig. 1 topology, relabeled for the supervisory challenge.

    Both occurrences of the original observable ``a`` leading to 4 and 9
    become ``o``; the other ``a`` edges are now unobservable.  The two
    branches are ``h a h o`` and ``u h a h o``.
    """
    return DFA.build(
        states=set(range(10)),
        alphabet={"a", "h", "o", "u"},
        initial=0,
        transitions={
            (0, "h"): 1,
            (1, "a"): 2,
            (2, "h"): 3,
            (3, "o"): 4,
            (0, "u"): 5,
            (5, "h"): 6,
            (6, "a"): 7,
            (7, "h"): 8,
            (8, "o"): 9,
        },
        secret_states={4},
    )


def build_example_5_bts():
    """Build manuscript Fig. 1 with only ``a`` controllable.

    Event ``o`` is observable and uncontrollable; ``h`` is releasable
    and uncontrollable, while ``a`` and ``u`` are unobservable.
    """
    from .supervisory import SupervisoryDIRMBTS

    bts = SupervisoryDIRMBTS(
        example_5_plant(),
        controllable={"a"},
        uncontrollable={"h", "o", "u"},
        observable={"o"},
        unobservable={"a", "u"},
        releasable={"h"},
        release_states={1, 4, 8},
    )
    bts.construct()
    return bts


def example_6_plant() -> DFA:
    """Return the six-state counterexample to merging J-states by low estimate.

    Prefixes ``h o1`` and ``h o2`` reach 2Y and 3Y. The hidden h-cycle makes
    their low estimates equal, while an immediate o3 releases different
    singleton estimates at secret state 4 and non-secret state 5.
    """
    return DFA.build(
        states=set(range(6)),
        alphabet={"h", "o1", "o2", "o3"},
        initial=0,
        transitions={
            (0, "h"): 1,
            (1, "o1"): 2,
            (1, "o2"): 3,
            (2, "h"): 3,
            (3, "h"): 2,
            (2, "o3"): 4,
            (3, "o3"): 5,
        },
        secret_states={4},
    )


def build_example_6_bts():
    """Build Example 6 with all events enabled and uncontrollable."""
    from .supervisory import SupervisoryDIRMBTS

    plant = example_6_plant()
    bts = SupervisoryDIRMBTS(
        plant,
        controllable=set(),
        uncontrollable=plant.alphabet,
        observable={"o1", "o2", "o3"},
        unobservable=set(),
        releasable={"h"},
        release_states={4, 5},
    )
    bts.construct()
    return bts


def build_figure_2_bts():
    """Backward-compatible alias for :func:`build_example_3_bts`."""
    return build_example_3_bts()

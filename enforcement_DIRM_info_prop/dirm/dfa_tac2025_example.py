"""User-provided DFA examples used by the DIRM supervisory-control demo."""

from __future__ import annotations

import sys
from pathlib import Path


# Allow both ``import dirm.dfa_tac2025_example`` and direct execution from
# PyCharm with ``python dirm/dfa_tac2025_example.py``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "dirm"

from .dfa import DFA


def user_example_1_plant() -> DFA:
    """Return project Example 1 (the corrected user-provided DFA)."""
    return DFA.build(
        states={"0", "1", "2", "3", "4", "5", "6"},
        alphabet={"a", "b", "uc", "o", "h1", "h2"},
        initial="0",
        transitions={
            ("0", "h1"): "1",
            ("1", "a"): "2",
            ("1", "b"): "3",
            ("0", "h2"): "6",
            ("2", "a"): "3",
            ("3", "a"): "4",
            ("4", "b"): "5",
            ("4", "o"): "3",
            ("4", "h2"): "6",
            ("5", "b"): "3",
            ("6", "uc"): "2",
        },
        secret_states={"3", "6"},
    )


def simplified_example_2_plant() -> DFA:
    """Return project Example 2, a compact form of Example 1.

    The two paths ``q_1 --b--> q_3`` and
    ``q_1 --a--> q_2 --a--> q_3`` are unchanged. The alternate branch is
    ``q_0 --uc--> q_6 --o--> q_2``. From ``q_4``, event ``b`` reaches
    ``q_5`` while ``a`` reaches ``q_6``. Their shared subsequent ``o``
    observation retains uncertainty between ``q_2`` and ``q_3`` at an I-state.
    The cycle ``4-a-6-h-4`` carries an ``h`` event without letting that
    event enter a release state directly. States 5 and 6 are secret, while
    states 2 and 5 are release states.
    """
    return DFA.build(
        states={"0", "1", "2", "3", "4", "5", "6"},
        alphabet={"a", "b", "h", "o", "uc"},
        initial="0",
        transitions={
            ("0", "h"): "1",
            ("0", "uc"): "6",
            ("1", "a"): "2",
            ("1", "b"): "3",
            ("2", "a"): "3",
            ("3", "uc"): "4",
            ("4", "b"): "5",
            ("4", "a"): "6",
            ("5", "o"): "3",
            ("6", "o"): "2",
            ("6", "h"): "4",
        },
        secret_states={"5", "6"},
    )


def untimed_iwa_release_example() -> DFA:
    """Backward-compatible alias for :func:`user_example_1_plant`."""
    return user_example_1_plant()


def _build_augmented(plant: DFA, release_states):
    from .augmented import AugmentedDFA

    return AugmentedDFA(
        plant,
        observable={"o"} & plant.alphabet,
        unobservable={"a", "b", "uc"} & plant.alphabet,
        releasable={"h", "h1", "h2"} & plant.alphabet,
        release_states=set(release_states) & plant.states,
    )


def build_user_example_1_augmented():
    """Return the augmented transition system for project Example 1."""
    return _build_augmented(user_example_1_plant(), {"2", "5"})


def build_simplified_example_2_augmented():
    """Return the augmented transition system for project Example 2."""
    return _build_augmented(simplified_example_2_plant(), {"2", "5"})


def build_untimed_iwa_augmented():
    """Backward-compatible alias for :func:`build_user_example_1_augmented`."""
    return build_user_example_1_augmented()


def _build_bts(plant: DFA, release_states, *, controllable_override=None):
    from .supervisory import SupervisoryDIRMBTS

    controllable = (
        {"a", "b", "h", "h1"} & plant.alphabet
        if controllable_override is None
        else set(controllable_override) & plant.alphabet
    )
    bts = SupervisoryDIRMBTS(
        plant,
        controllable=controllable,
        uncontrollable=plant.alphabet - controllable,
        observable={"o"} & plant.alphabet,
        unobservable={"a", "b", "uc"} & plant.alphabet,
        releasable={"h", "h1", "h2"} & plant.alphabet,
        release_states=set(release_states) & plant.states,
    )
    bts.construct()
    return bts


def build_user_example_1_bts():
    """Return the supervisory DIRM system for project Example 1."""
    return _build_bts(user_example_1_plant(), {"2", "5"})


def build_simplified_example_2_bts():
    """Return the supervisory DIRM system for project Example 2."""
    return _build_bts(
        simplified_example_2_plant(), {"2", "5"},
        controllable_override={"a", "b", "h"},
    )


def build_untimed_iwa_bts():
    """Backward-compatible alias for :func:`build_user_example_1_bts`."""
    return build_user_example_1_bts()


if __name__ == "__main__":
    # Running this definition file directly executes all supervisory examples.
    from dirm_supervisory_demo import main

    main()

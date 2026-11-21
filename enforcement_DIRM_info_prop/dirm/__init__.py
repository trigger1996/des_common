"""Theory-only verification of current-state opacity under DIRM.

The package is deliberately independent from :mod:`opacity_iwa`: the latter
keeps the timed IWA research code, whereas this package implements the DFA
construction in Hou, Yin and Li (Automatica, 2022).
"""

from .dfa import DFA, DFAError, State
from .augmented import AugmentedDFA, AugmentedState
from .observer import DIRMObserver, ObserverState
from .verification import OpacityResult, verify_current_state_opacity
from .export import export_observer
from .augmented_export import export_augmented_system, write_augmented_comparison
from .supervisory import (
    BTSEdge,
    SynthesisResult,
    SupervisoryDIRMBTS,
    IState,
    JState,
    LState,
)
from .paper_example import (
    build_example_3_bts,
    build_example_4_bts,
    build_example_5_bts,
    build_example_6_bts,
    build_figure_2_bts,
    example_3_plant,
    example_4_plant,
    example_5_plant,
    example_6_plant,
)
from .dfa_tac2025_example import (
    build_simplified_example_2_augmented,
    build_simplified_example_2_bts,
    build_untimed_iwa_augmented,
    build_untimed_iwa_bts,
    build_user_example_1_augmented,
    build_user_example_1_bts,
    simplified_example_2_plant,
    untimed_iwa_release_example,
    user_example_1_plant,
)
from .supervisory_export import export_supervisory_bts
from .plant_export import export_plant

__all__ = [
    "DFA", "DFAError", "State", "AugmentedDFA", "AugmentedState",
    "DIRMObserver", "ObserverState", "OpacityResult",
    "verify_current_state_opacity", "export_observer", "export_augmented_system",
    "write_augmented_comparison",
    "IState", "JState", "LState", "BTSEdge", "SynthesisResult",
    "SupervisoryDIRMBTS", "user_example_1_plant", "simplified_example_2_plant",
    "untimed_iwa_release_example",
    "build_user_example_1_augmented", "build_simplified_example_2_augmented",
    "build_user_example_1_bts", "build_simplified_example_2_bts",
    "build_untimed_iwa_augmented", "build_untimed_iwa_bts",
    "export_supervisory_bts", "export_plant", "example_3_plant", "build_example_3_bts",
    "example_4_plant", "build_example_4_bts",
    "example_5_plant", "build_example_5_bts",
    "example_6_plant", "build_example_6_bts", "build_figure_2_bts",
]

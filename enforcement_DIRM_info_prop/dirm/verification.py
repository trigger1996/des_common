"""Current-state-opacity verification over a constructed DIRM-observer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .observer import DIRMObserver, ObserverState


@dataclass(frozen=True)
class OpacityResult:
    """The verification outcome and a shortest violating plant word, if any."""

    opaque: bool
    violating_state: Optional["ObserverState"] = None
    witness: Tuple[str, ...] = ()


def verify_current_state_opacity(observer: "DIRMObserver") -> OpacityResult:
    """Implement Theorem 2 by searching the reachable DIRM-observer.

    The plant is not opaque exactly when the third component of a reachable
    observer state is nonempty and contains original states that are all
    secret.  The recorded BFS word is a shortest counterexample.
    """
    graph, words = observer.reachable()
    for state in graph:
        estimate = {original for original, _ in state.q}
        if estimate and estimate <= observer.plant.secret_states:
            return OpacityResult(False, state, words[state])
    return OpacityResult(True)

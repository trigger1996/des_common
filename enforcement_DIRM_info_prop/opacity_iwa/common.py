"""Small, side-effect-free helpers shared by the two IWA constructions."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable, Iterator, List, TypeVar


Item = TypeVar("Item")


def nonempty_subsets(items: Iterable[Item]) -> Iterator[List[Item]]:
    """Yield every non-empty subset, preserving the input order.

    Policies in the legacy algorithms are lists, so this intentionally yields
    lists instead of tuples.  It replaces duplicated nested loops without
    changing their order or policy representation.
    """

    values = tuple(items)
    return (list(subset) for size in range(1, len(values) + 1)
            for subset in combinations(values, size))

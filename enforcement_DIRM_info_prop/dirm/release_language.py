"""Resolve labeled release transitions recursively through SCC supernodes.

Internal transitions of each strongly connected component are summarized by a
Kleene closure.  Release outcomes are then propagated backward through the
acyclic component graph and mapped back to the original estimate nodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Mapping, TypeVar


Node = TypeVar("Node", bound=Hashable)
Outcome = TypeVar("Outcome", bound=Hashable)


@dataclass(frozen=True)
class Language:
    kind: str
    parts: tuple["Language", ...] = ()
    symbol: str = ""

    def __str__(self) -> str:
        if self.kind == "empty":
            return "∅"
        if self.kind == "epsilon":
            return "ε"
        if self.kind == "symbol":
            return self.symbol
        if self.kind == "union":
            return "|".join(str(part) for part in self.parts)
        if self.kind == "concat":
            rendered = []
            for part in self.parts:
                value = str(part)
                if part.kind == "union":
                    value = f"({value})"
                rendered.append(value)
            separator = "" if all(
                (part.kind == "symbol" and len(part.symbol) == 1)
                or (
                    part.kind in {"star", "plus"}
                    and part.parts[0].kind == "symbol"
                    and len(part.parts[0].symbol) == 1
                )
                for part in self.parts
            ) else "·"
            return separator.join(rendered)
        if self.kind in {"star", "plus"}:
            child = self.parts[0]
            value = str(child)
            if child.kind not in {"symbol", "star", "plus"}:
                value = f"({value})"
            return value + ("^*" if self.kind == "star" else "^+")
        raise ValueError(f"unknown language kind: {self.kind}")


EMPTY = Language("empty")
EPSILON = Language("epsilon")


def symbol(event: str) -> Language:
    return Language("symbol", symbol=event)


def union(*expressions: Language) -> Language:
    parts = set()
    for expression in expressions:
        if expression == EMPTY:
            continue
        if expression.kind == "union":
            parts.update(expression.parts)
        else:
            parts.add(expression)
    if not parts:
        return EMPTY
    for part in tuple(parts):
        if part.kind == "plus" and EPSILON in parts:
            parts.discard(part)
            parts.discard(EPSILON)
            parts.add(star(part.parts[0]))
    if len(parts) == 1:
        return next(iter(parts))
    ordered = tuple(sorted(parts, key=str))
    factors = tuple(
        expression.parts if expression.kind == "concat" else (expression,)
        for expression in ordered
    )
    common_prefix = 0
    while all(len(term) > common_prefix for term in factors) and all(
        term[common_prefix] == factors[0][common_prefix] for term in factors
    ):
        common_prefix += 1
    if common_prefix:
        return concat(
            *factors[0][:common_prefix],
            union(*(concat(*term[common_prefix:]) for term in factors)),
        )
    common_suffix = 0
    while all(len(term) > common_suffix for term in factors) and all(
        term[-common_suffix - 1] == factors[0][-common_suffix - 1]
        for term in factors
    ):
        common_suffix += 1
    if common_suffix:
        return concat(
            union(*(concat(*term[:-common_suffix]) for term in factors)),
            *factors[0][-common_suffix:],
        )
    return Language("union", ordered)


def concat(*expressions: Language) -> Language:
    parts = []
    for expression in expressions:
        if expression == EMPTY:
            return EMPTY
        if expression == EPSILON:
            continue
        if expression.kind == "concat":
            parts.extend(expression.parts)
        else:
            parts.append(expression)
    index = 0
    while index + 1 < len(parts):
        if parts[index + 1].kind == "star" and parts[index] == parts[index + 1].parts[0]:
            parts[index:index + 2] = [Language("plus", (parts[index],))]
        else:
            index += 1
    if not parts:
        return EPSILON
    if len(parts) == 1:
        return parts[0]
    return Language("concat", tuple(parts))


def star(expression: Language) -> Language:
    if expression in {EMPTY, EPSILON}:
        return EPSILON
    if expression.kind in {"star", "plus"}:
        return Language("star", expression.parts)
    if expression.kind == "union" and EPSILON in expression.parts:
        return star(union(*(part for part in expression.parts if part != EPSILON)))
    return Language("star", (expression,))


def _components(graph: Mapping[Node, tuple[tuple[str, Node], ...]]) -> list[tuple[Node, ...]]:
    """Tarjan SCCs, returned in reverse topological order."""
    index = 0
    indices: dict[Node, int] = {}
    low: dict[Node, int] = {}
    stack: list[Node] = []
    on_stack: set[Node] = set()
    result: list[tuple[Node, ...]] = []

    def visit(node: Node) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for _, target in graph[node]:
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            result.append(tuple(component))

    for node in graph:
        if node not in indices:
            visit(node)
    return result


def _internal_closure(
    component: tuple[Node, ...], graph: Mapping[Node, tuple[tuple[str, Node], ...]]
) -> dict[tuple[Node, Node], Language]:
    """All finite paths between nodes of one SCC, including empty paths."""
    if len(component) == 1:
        node = component[0]
        return {(node, node): star(union(*(
            symbol(event) for event, target in graph[node] if target == node
        )))}
    members = set(component)
    routes = {(source, target): EMPTY for source in component for target in component}
    for source in component:
        for event, target in graph[source]:
            if target in members:
                routes[source, target] = union(routes[source, target], symbol(event))
    for middle in component:
        old = routes
        routes = {
            (source, target): union(
                old[source, target],
                concat(
                    old[source, middle],
                    star(old[middle, middle]),
                    old[middle, target],
                ),
            )
            for source in component for target in component
        }
    for node in component:
        routes[node, node] = union(EPSILON, routes[node, node])
    return routes


def recursive_transition_labels(
    graph: Mapping[Node, tuple[tuple[str, Node], ...]],
    start: Node,
    direct: Mapping[Node, Mapping[Outcome, Language]],
) -> dict[Outcome, Language]:
    """Solve release outcomes and labels directly on the SCC condensation.

    ``direct[node]`` gives the terminal release outcomes available at that
    node, labeled only by the terminal observation.  A returned outcome is a
    transition of the original start node; its value is the finite expression
    produced by the recursive supernode calculation.
    """
    components = _components(graph)
    owner = {node: index for index, group in enumerate(components) for node in group}
    resolved: dict[Node, dict[Outcome, Language]] = {}
    # Tarjan emits sinks first.  Every external successor has therefore
    # already been resolved when its predecessor supernode is processed.
    for group in components:
        closure = _internal_closure(group, graph)
        exits: dict[Node, dict[Outcome, Language]] = {}
        for node in group:
            available = dict(direct.get(node, {}))
            for event, successor in graph[node]:
                if owner[node] != owner[successor]:
                    for outcome, language in resolved[successor].items():
                        available[outcome] = union(
                            available.get(outcome, EMPTY),
                            concat(symbol(event), language),
                        )
            exits[node] = available
        for node in group:
            available = {}
            for exit_node in group:
                internal = closure[node, exit_node]
                for outcome, language in exits[exit_node].items():
                    available[outcome] = union(
                        available.get(outcome, EMPTY),
                        concat(internal, language),
                    )
            resolved[node] = available
    return resolved[start]

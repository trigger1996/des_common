"""Compatibility aliases for the NetworkX 1.x API used by legacy IWA code."""

import networkx as nx


def enable_legacy_api() -> None:
    for graph_type in (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph):
        if not hasattr(graph_type, "node"):
            graph_type.node = property(lambda graph: graph._node)
        if not hasattr(graph_type, "edge"):
            graph_type.edge = property(lambda graph: graph._adj)

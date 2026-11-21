"""Reader for the small IWA YAML dialect stored in this repository.

The legacy IWA examples used ``yaml.load`` but did not declare PyYAML as a
dependency. Keeping the reader local makes the theory examples runnable in a
minimal Python environment. It intentionally accepts only the graph format in
``opacity_iwa/iwa/*.yaml``; it is not a general YAML parser.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, TextIO


def _value(value: str) -> Any:
    value = value.strip()
    if value.startswith(("'", '"')):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def load(stream: TextIO) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges = []
    section = None
    node_pattern = re.compile(r"^\s{4}'([^']+)'\s*:\s*(.*)$")
    edge_pattern = re.compile(r"^\s*-\s*\[\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*\{(.*)\}\s*\]\s*$")
    for raw_line in stream:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "nodes:":
            section = "nodes"
        elif stripped == "edges:":
            section = "edges"
        elif not stripped or stripped.startswith("#!"):
            continue
        elif section == "nodes":
            match = node_pattern.match(line)
            if match:
                name, inline = match.groups()
                nodes[name] = {} if inline == "{}" else {"prop": {"secret"}}
        elif section == "edges":
            match = edge_pattern.match(line)
            if match:
                source, target, attributes = match.groups()
                data = {}
                for item in attributes.split(","):
                    key, value = item.split(":", 1)
                    data[key.strip()] = _value(value)
                edges.append([source, target, data])
    return {"graph": {"nodes": nodes, "edges": edges}}

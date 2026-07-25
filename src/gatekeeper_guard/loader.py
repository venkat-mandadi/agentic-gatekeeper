"""Load Kubernetes resources into the engine.

Accepts what you already have: a ``kubectl get ... -o json`` dump (a single
resource, a List, or an array), or a YAML manifest stream if PyYAML is present.
No hard dependency on a Kubernetes client — the engine works on plain dicts.
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import Resource


def _wrap(items: list[dict]) -> list[Resource]:
    return [Resource(x) for x in items if isinstance(x, dict) and x.get("kind")]


def from_json(text: str) -> list[Resource]:
    data = json.loads(text)
    if isinstance(data, dict) and data.get("kind") == "List":
        return _wrap(data.get("items", []))
    if isinstance(data, dict):
        return _wrap([data])
    if isinstance(data, list):
        return _wrap(data)
    return []


def from_yaml(text: str) -> list[Resource]:  # pragma: no cover - optional dep
    try:
        import yaml
    except ImportError as e:
        raise SystemExit("PyYAML is required for YAML input. Use JSON, or `pip install pyyaml`.") from e
    docs = [d for d in yaml.safe_load_all(text) if isinstance(d, dict)]
    items: list[dict] = []
    for d in docs:
        if d.get("kind") == "List":
            items.extend(d.get("items", []))
        else:
            items.append(d)
    return _wrap(items)


def load(path: str | Path) -> list[Resource]:
    p = Path(path)
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        return from_yaml(text)
    return from_json(text)

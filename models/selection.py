"""Saved model default. The router reads this file on every choice."""

from __future__ import annotations

import json
import os
from typing import Optional

DEFAULT_PATH = "/home/pip/.config/pip/model.json"


def config_path() -> str:
    return os.environ.get("PIP_MODEL_CONFIG", DEFAULT_PATH)


def read_default() -> Optional[str]:
    path = config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    name = data.get("default")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def write_default(name: str) -> str:
    path = config_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"default": name}, handle)
    return path

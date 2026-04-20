"""Configuration loading with a PyYAML-free fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dpcr_ids.exceptions import ConfigurationError


def _expand_env_vars(text: str) -> str:
    return os.path.expandvars(text)


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigurationError(f"Config file does not exist: {config_path}")

    raw_text = _expand_env_vars(config_path.read_text(encoding="utf-8-sig"))
    if not raw_text.strip():
        raise ConfigurationError(f"Config file is empty: {config_path}")

    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                "PyYAML is not installed and the config is not JSON-compatible YAML."
            ) from exc
    else:
        data = yaml.safe_load(raw_text)

    if not isinstance(data, dict):
        raise ConfigurationError(f"Expected a mapping at top-level config: {config_path}")
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def require_keys(config: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in config]
    if missing:
        raise ConfigurationError(f"Missing required config keys: {', '.join(missing)}")


"""Helpers for optional dependencies."""

from __future__ import annotations

import importlib

from dpcr_ids.exceptions import DependencyUnavailableError


def require_dependency(module_name: str, extra: str | None = "ml"):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        suffix = f" Install with `pip install -e .[{extra}]`." if extra else "."
        raise DependencyUnavailableError(
            f"Optional dependency `{module_name}` is required for this command.{suffix}"
        ) from exc

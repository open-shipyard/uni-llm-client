# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Vendor-neutral reasoning effort, as specified in docs/specs/effort.md."""

from collections.abc import Collection
from enum import StrEnum


class Effort(StrEnum):
    """How much the model should reason before answering."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


_ORDER = tuple(Effort)


def parse_effort(effort: Effort | str | None) -> Effort | None:
    """Validate a user-supplied effort, raising `ValueError` if invalid (EFFORT-1)."""
    return None if effort is None else Effort(effort)


def resolve_effort(requested: Effort, supported: Collection[Effort]) -> Effort:
    """Return the nearest supported level, rounding up (EFFORT-4)."""
    ranked = sorted(supported, key=_ORDER.index)
    for level in ranked:
        if _ORDER.index(level) >= _ORDER.index(requested):
            return level
    return ranked[-1]

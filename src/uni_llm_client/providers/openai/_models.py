# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""What each OpenAI model supports. Update when OpenAI ships or retires models."""

import re
from collections.abc import Mapping

from uni_llm_client._effort import Effort

LOW, MEDIUM, HIGH, MAX = Effort

# Values each model accepts for reasoning.effort, keyed by the level they implement.
# Models without "max" implement MAX with their highest level (EFFORT-4).
_UP_TO_HIGH = {LOW: "low", MEDIUM: "medium", HIGH: "high"}
_UP_TO_XHIGH = {**_UP_TO_HIGH, MAX: "xhigh"}
_UP_TO_MAX = {**_UP_TO_HIGH, MAX: "max"}
_PRO = {MEDIUM: "medium", HIGH: "high", MAX: "xhigh"}

MODELS: dict[str, Mapping[Effort, str]] = {
    "gpt-6-astra": _UP_TO_MAX,
    "gpt-5.6-sol": _UP_TO_MAX,
    "gpt-5.6-terra": _UP_TO_MAX,
    "gpt-5.6-luna": _UP_TO_MAX,
    "gpt-5.5": _UP_TO_XHIGH,
    "gpt-5.5-pro": _PRO,
    "gpt-5.4": _UP_TO_XHIGH,
    "gpt-5.4-pro": _PRO,
    "gpt-5.3-codex": _UP_TO_XHIGH,
    "gpt-5.2": _UP_TO_XHIGH,
    "gpt-5.2-pro": _PRO,
    "gpt-5.1": _UP_TO_HIGH,
    "gpt-5": _UP_TO_HIGH,
    "gpt-5-mini": _UP_TO_HIGH,
    "gpt-5-nano": _UP_TO_HIGH,
    "gpt-5-pro": {HIGH: "high"},
    "o3": _UP_TO_HIGH,
    "o3-pro": _UP_TO_HIGH,
    "o4-mini": _UP_TO_HIGH,
}

_SNAPSHOT_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def lookup_model(model: str) -> Mapping[Effort, str] | None:
    """Return the efforts `model` supports, or `None` if it is not in the table."""
    return MODELS.get(_SNAPSHOT_SUFFIX.sub("", model))

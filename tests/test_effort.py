# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

import pytest

from uni_llm_client import Effort
from uni_llm_client._effort import resolve_effort

LOW, MEDIUM, HIGH, MAX = Effort


@pytest.mark.parametrize(
    ("requested", "supported", "expected"),
    [
        (HIGH, {LOW, MEDIUM, HIGH, MAX}, HIGH),
        (LOW, {MEDIUM, HIGH}, MEDIUM),
        (MEDIUM, {LOW, HIGH}, HIGH),
        (HIGH, {LOW, MEDIUM}, MEDIUM),
        (MAX, {LOW, HIGH}, HIGH),
    ],
)
def test_resolves_to_the_nearest_supported_level_rounding_up(
    requested: Effort, supported: set[Effort], expected: Effort
) -> None:
    assert resolve_effort(requested, supported) == expected

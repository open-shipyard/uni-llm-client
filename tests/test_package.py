# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

import importlib
import importlib.metadata
from importlib.metadata import PackageNotFoundError, version

import pytest

import uni_llm_client


def test_version_matches_distribution_metadata() -> None:
    assert uni_llm_client.__version__ == version("uni-llm-client")


def test_imports_without_distribution_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_installed(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", not_installed)
    try:
        assert importlib.reload(uni_llm_client).__version__ == "0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(uni_llm_client)

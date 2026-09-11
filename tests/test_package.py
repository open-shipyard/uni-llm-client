# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

from importlib.metadata import version

import uni_llm_client


def test_version_matches_distribution_metadata() -> None:
    assert uni_llm_client.__version__ == version("uni-llm-client")

# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Abstract LLM APIs behind a common signature."""

from importlib.metadata import version

__version__ = version("uni-llm-client")

__all__ = ["__version__"]

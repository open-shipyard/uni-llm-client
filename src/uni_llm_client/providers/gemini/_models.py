# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""What each Gemini model supports. Update when Google ships or retires models."""

# Token-budget models and the largest thinking budget each accepts, used for MAX.
# Every other model, including all current Gemini 3.x models, takes a thinking
# level of low, medium or high.
MAX_THINKING_BUDGETS: dict[str, int] = {
    "gemini-2.5-pro": 32_768,
    "gemini-2.5-flash": 24_576,
    "gemini-2.5-flash-lite": 24_576,
}

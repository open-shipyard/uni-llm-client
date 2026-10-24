# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""The events of a stream, as specified in docs/specs/streaming.md."""

from __future__ import annotations

from dataclasses import dataclass

from uni_llm_client._messages import Response, ToolUseBlock


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ToolUseStart:
    """The model started a tool call; its input follows as `ToolUseDelta`s."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class ToolUseDelta:
    """A piece of the JSON text of a tool call's input."""

    id: str
    partial_json: str


@dataclass(frozen=True, slots=True)
class ToolUseEnd:
    """A tool call whose input is complete."""

    block: ToolUseBlock


@dataclass(frozen=True, slots=True)
class Completed:
    """The last event of a stream: the response `complete` would have returned."""

    response: Response


StreamEvent = (
    TextDelta | ReasoningDelta | ToolUseStart | ToolUseDelta | ToolUseEnd | Completed
)

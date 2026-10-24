# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Server-sent events, decoded line by line and without I/O."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServerSentEvent:
    event: str
    """The ``event`` field, or ``"message"`` when the event has none."""

    data: str
    """The ``data`` lines, joined with newlines."""


class SSEDecoder:
    """Feed it each line of the response, without its line ending."""

    def __init__(self) -> None:
        self._event = ""
        self._data: list[str] = []

    def feed(self, line: str) -> ServerSentEvent | None:
        """The event the line completes, if it completes one."""
        if line == "":
            return self._dispatch()
        if line.startswith(":"):
            return None  # a comment, such as a vendor's keep-alive
        name, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if name == "event":
            self._event = value
        elif name == "data":
            self._data.append(value)
        # `id` and `retry` are for reconnecting, which this library does not do.
        return None

    def _dispatch(self) -> ServerSentEvent | None:
        if not self._data:
            self._event = ""
            return None
        event = ServerSentEvent(self._event or "message", "\n".join(self._data))
        self._event = ""
        self._data = []
        return event

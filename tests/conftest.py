# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Runs every case against every implementation listed in implementations.json.

The mock vendor records each request it receives and serves the responses a case
gives it. Each implementation's test server sends its vendor requests there.
"""

import json
import os
import re
import select
import subprocess
import threading
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).parent
REPO = HERE.parent
IMPLEMENTATIONS: dict[str, dict[str, Any]] = json.loads(
    (HERE / "implementations.json").read_text()
)
STARTUP_TIMEOUT = 120.0  # The first `uv run` may install the environment.

# Calls to 127.0.0.1 must not go through a proxy from the environment.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@dataclass
class VendorCall:
    method: str
    url: str
    headers: dict[str, str]
    json: Any


class MockVendor:
    """Records the requests it receives and serves the responses it is given."""

    def __init__(self) -> None:
        self.calls: list[VendorCall] = []
        self._responses: list[dict[str, Any]] = []
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host!s}:{port}"

    def serve(self, responses: list[dict[str, Any]]) -> None:
        self.calls.clear()
        self._responses = list(responses)

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        vendor = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                headers = {k.lower(): v for k, v in self.headers.items()}
                vendor.calls.append(
                    VendorCall(
                        method=self.command,
                        # Implementations keep the vendor's Host header and path.
                        url=f"https://{headers.get('host')}{self.path}",
                        headers=headers,
                        json=json.loads(body) if body else None,
                    )
                )
                if vendor._responses:
                    response = vendor._responses.pop(0)
                else:
                    response = {"status": 500, "body": {"error": "no response left"}}
                if "events" in response:
                    reply = sse(response["events"])
                    content_type = "text/event-stream"
                else:
                    reply = json.dumps(response["body"]).encode()
                    content_type = "application/json"
                self.send_response(response["status"])
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        return Handler


def sse(events: list[dict[str, Any]]) -> bytes:
    """Server-sent events: each has a `data`, an optional `event`, or a `comment`."""
    frames = []
    for event in events:
        if "comment" in event:
            frames.append(f": {event['comment']}\n\n")
            continue
        data = event["data"]
        text = data if isinstance(data, str) else json.dumps(data)
        name = f"event: {event['event']}\n" if "event" in event else ""
        frames.append(f"{name}data: {text}\n\n")
    return "".join(frames).encode()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--impl",
        action="append",
        choices=sorted(IMPLEMENTATIONS),
        help="Implementation to test; repeat for several. Default: all.",
    )
    parser.addoption(
        "--package",
        action="append",
        choices=sorted({spec["package"] for spec in IMPLEMENTATIONS.values()}),
        help="Test every implementation of a package; repeat for several.",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "implementation" in metafunc.fixturenames:
        names = metafunc.config.getoption("impl") or []
        for package in metafunc.config.getoption("package") or []:
            names += [n for n, s in IMPLEMENTATIONS.items() if s["package"] == package]
        names = sorted(set(names)) or sorted(IMPLEMENTATIONS)
        metafunc.parametrize("implementation", names, indirect=True, scope="session")


@pytest.fixture(scope="session")
def mock_vendor() -> Iterator[MockVendor]:
    vendor = MockVendor()
    yield vendor
    vendor.close()


@pytest.fixture
def vendor(mock_vendor: MockVendor) -> MockVendor:
    mock_vendor.serve([])
    return mock_vendor


@pytest.fixture(scope="session")
def implementation(
    request: pytest.FixtureRequest, mock_vendor: MockVendor
) -> Iterator[str]:
    """Start the implementation's test server and return its URL."""
    spec = IMPLEMENTATIONS[request.param]
    # Real API keys stay out of reach: the cases pass the keys they need.
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    process = subprocess.Popen(
        [*spec["command"], "--vendor-url", mock_vendor.url],
        cwd=REPO / spec["cwd"],
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    try:
        ready, _, _ = select.select([process.stdout], [], [], STARTUP_TIMEOUT)
        line = process.stdout.readline() if ready else ""
        match = re.fullmatch(r"listening on (\S+)\n", line)
        if not match:
            pytest.fail(f"{request.param} did not start; first line: {line!r}")
        yield match[1]
    finally:
        process.terminate()
        process.wait(timeout=10)


def call(server_url: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """POST `args` to the test server's `/name` and return its reply."""
    request = urllib.request.Request(
        f"{server_url}/{name}",
        data=json.dumps(args).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with _opener.open(request) as response:
            reply: dict[str, Any] = json.load(response)
    except urllib.error.HTTPError as error:
        pytest.fail(f"The test server failed:\n{error.read().decode()}")
    return reply

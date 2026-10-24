# Copyright 2026 The uni-llm-client Authors
# SPDX-License-Identifier: Apache-2.0

"""Serves `ask` over HTTP for the language-agnostic tests in the repository root.

Run ``python tests/server.py --vendor-url URL [--client sync|async]``. Every
vendor request goes to `URL`, keeping its path and ``Host`` header. The protocol
is in ``tests/README.md`` at the repository root.
"""

import argparse
import asyncio
import json
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import httpx2

from uni_llm_client import (
    AsyncClient,
    AuthenticationError,
    Client,
    IncompleteResponseError,
    ProviderError,
    RateLimitError,
    RefusalError,
)

# Most specific first: the subclasses of ProviderError come before it.
ERROR_TYPES: list[tuple[type[Exception], str]] = [
    (ValueError, "invalid_argument"),
    (AuthenticationError, "authentication"),
    (RateLimitError, "rate_limit"),
    (RefusalError, "refusal"),
    (IncompleteResponseError, "incomplete_response"),
    (ProviderError, "provider"),
]


def redirect(request: httpx2.Request, vendor_url: httpx2.URL) -> None:
    request.url = request.url.copy_with(
        scheme=vendor_url.scheme, host=vendor_url.host, port=vendor_url.port
    )


class RedirectTransport(httpx2.HTTPTransport):
    def __init__(self, vendor_url: httpx2.URL) -> None:
        super().__init__()
        self.vendor_url = vendor_url

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        redirect(request, self.vendor_url)
        return super().handle_request(request)


class AsyncRedirectTransport(httpx2.AsyncHTTPTransport):
    def __init__(self, vendor_url: httpx2.URL) -> None:
        super().__init__()
        self.vendor_url = vendor_url

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        redirect(request, self.vendor_url)
        return await super().handle_async_request(request)


def ask_sync(vendor_url: httpx2.URL, args: dict[str, Any]) -> str:
    # trust_env=False: a proxy from the environment would bypass the transport.
    http_client = httpx2.Client(
        transport=RedirectTransport(vendor_url), trust_env=False
    )
    with Client(api_keys=args.get("api_keys"), http_client=http_client) as client:
        return client.ask(
            args["model"],
            args["question"],
            web_search=args.get("web_search", False),
            effort=args.get("effort"),
        )


def ask_async(vendor_url: httpx2.URL, args: dict[str, Any]) -> str:
    async def run() -> str:
        http_client = httpx2.AsyncClient(
            transport=AsyncRedirectTransport(vendor_url), trust_env=False
        )
        async with AsyncClient(
            api_keys=args.get("api_keys"), http_client=http_client
        ) as client:
            return await client.ask(
                args["model"],
                args["question"],
                web_search=args.get("web_search", False),
                effort=args.get("effort"),
            )

    return asyncio.run(run())


def error_type(error: Exception) -> str | None:
    for cls, name in ERROR_TYPES:
        if isinstance(error, cls):
            return name
    return None


def make_handler(vendor_url: httpx2.URL, client: str) -> type[BaseHTTPRequestHandler]:
    ask = ask_sync if client == "sync" else ask_async

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/ask":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0))
            args = json.loads(self.rfile.read(length))
            status = 200
            try:
                reply: dict[str, Any] = {"answer": ask(vendor_url, args)}
            except Exception as error:
                name = error_type(error)
                if name is None:
                    # A bug in this server or the library: show it to the runner.
                    status, reply = 500, {"traceback": traceback.format_exc()}
                else:
                    reply = {"error": {"type": name, "message": str(error)}}
            body = json.dumps(reply).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor-url", required=True)
    parser.add_argument("--client", choices=["sync", "async"], default="sync")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    handler = make_handler(httpx2.URL(args.vendor_url), args.client)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    host, port = server.server_address[:2]
    print(f"listening on http://{host!s}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

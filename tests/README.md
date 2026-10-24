# Language-agnostic tests

These tests check that every port sends the same vendor requests. Each port
ships a test server that exposes `ask` over HTTP. The tests start a mock vendor,
start the port's test server, and ask it questions. The mock vendor records each
request it receives, and each test compares those requests with its case.

## Running

The tests need [uv](https://docs.astral.sh/uv/). Run every implementation, or
one with `--impl`:

    cd tests
    uv run pytest
    uv run pytest --impl python-async

## Cases

Cases are data, in `cases/*.json`. Each case is an object:

| Key | Meaning |
|---|---|
| `name` | The test id. |
| `ask` | The arguments of `ask`: `model`, `question`, and optionally `web_search`, `effort` and `api_keys`. |
| `responses` | Optional. A file in `vendor_responses/`, without `.json`: the responses the mock vendor serves, in order. |
| `requests` | The vendor requests expected, in order. Each has `method`, `url`, `headers` and `json`. |
| `answer` | The answer expected. |
| `error` | The error type expected, instead of `answer`. |

The `json` of a request must match exactly. Its `headers` must be present with
these values, and other headers are allowed. Every case passes the API key
`test-key` for each provider, unless it sets `api_keys`.

A new behaviour usually needs a new case. A new vendor needs its responses in
`vendor_responses/<provider>/`.

## Test server protocol

Each port's test server lives in its own `tests/` directory and is listed in
`implementations.json`. The runner starts the `command` in `cwd`, relative to
the repository root, and appends `--vendor-url URL`.

1. The server listens on a free port of `127.0.0.1`. Its first line on stdout
   is `listening on http://127.0.0.1:PORT`.
2. The server sends every vendor request to `URL`. Each request keeps its
   method, path, query, headers and body. The `Host` header keeps the vendor's
   host, such as `api.anthropic.com`.
3. `POST /ask` takes the arguments of `ask` as a JSON object. It calls `ask`
   with a new client created with the given `api_keys`.
4. The server replies with status 200 and `{"answer": "..."}`, or
   `{"error": {"type": "...", "message": "..."}}` when `ask` raises a library
   error.
5. Any other failure replies with status 500. Its body helps debugging.

The runner removes every environment variable ending in `_API_KEY` before it
starts a server.

Error types are the same in every port:

| Type | Raised when |
|---|---|
| `invalid_argument` | An argument is invalid, such as the model id or the effort. |
| `authentication` | The API key is missing or rejected. |
| `rate_limit` | The vendor rate-limits the request. |
| `refusal` | The model declines to answer. |
| `incomplete_response` | The response contains no complete answer. |
| `provider` | Any other vendor error. |

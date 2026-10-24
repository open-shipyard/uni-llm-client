# Retries

Status: Draft

`Client` and `AsyncClient` send a failed model call again when another attempt
may pass.

## Invariants

- **RETRY-1**: `max_retries` counts the retries after the first attempt. It is 2
  by default, and 0 turns retries off. A negative value raises `ValueError`.
- **RETRY-2**: HTTP 408, 409, 429 and 5xx are retried, and so are connection
  failures and timeouts. An error in the body of a 200 is retried by its status
  code. Nothing else is retried.
- **RETRY-3**: The wait before retry `n` is `min(0.5 × 2^(n-1), 8)` seconds, less
  up to a quarter at random.
- **RETRY-4**: A `retry-after-ms` or `retry-after` of 0 to 60 seconds replaces
  that wait.
- **RETRY-5**: A connection failure or a timeout raises `TransportError`.
- **RETRY-6**: The last attempt's error is raised once the retries are spent.
- **RETRY-7**: A stream is retried only until the vendor answers with a success
  status.
- **RETRY-8**: A retry sends the same request. `ask` retries each request of
  its `pause_turn` loop on its own.

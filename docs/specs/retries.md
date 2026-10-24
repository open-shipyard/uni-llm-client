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
- **RETRY-3**: The wait before retry `n` is
  `min(initial_retry_delay × 2^(n-1), max_retry_delay)` seconds, less up to a
  quarter at random. The two options are 0.5 and 8 by default.
- **RETRY-4**: A `retry-after-ms` or `retry-after` of 0 to `max_retry_after`
  seconds replaces that wait. `max_retry_after` is 60 by default.
- **RETRY-5**: A connection failure or a timeout raises `TransportError`.
- **RETRY-6**: The last attempt's error is raised once the retries are spent.
- **RETRY-7**: A stream is retried only until the vendor answers with a success
  status.
- **RETRY-8**: A retry sends the same request. `ask` retries each request of
  its `pause_turn` loop on its own.
- **RETRY-9**: `initial_retry_delay`, `max_retry_delay` and `max_retry_after`
  are options of the client. A negative or non-finite value raises `ValueError`.

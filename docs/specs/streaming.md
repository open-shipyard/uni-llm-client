# Streaming

Status: Draft

## Scope

`stream`: the inputs of `complete` ([messages.md](messages.md)), and an
iterator of events instead of a response.

## Events

| Event | Fields | Meaning |
|---|---|---|
| `TextDelta` | `text` | A piece of a text block. |
| `ReasoningDelta` | `text` | A piece of a reasoning block. |
| `ToolUseStart` | `id`, `name` | The model started a tool call. |
| `ToolUseDelta` | `id`, `partial_json` | A piece of the JSON text of the call's input. |
| `ToolUseEnd` | `block` | The call, its input complete. |
| `Completed` | `response` | The response `complete` would have returned. |

## Invariants

- **STREAM-1**: The request is the one `complete` sends, plus the vendor's
  streaming flag. Nothing else differs.
- **STREAM-2**: Events come in the order the content arrives. A tool call is
  `ToolUseStart`, then its `ToolUseDelta`s, then `ToolUseEnd`, and the deltas
  joined are the JSON text of the block's input. Empty pieces are not yielded.
- **STREAM-3**: `Completed` is last, exactly once, and carries the response
  `complete` would have returned for the same message: the same blocks, stop
  reason, usage and `vendor` content, so that the message replays the same.
- **STREAM-4**: A stream that ends before the vendor marked the message
  complete raises `IncompleteResponseError`. An error the vendor sends during
  the stream raises the error it maps to, as in `complete`.
- **STREAM-5**: Nothing is sent before the first iteration, so MSG-1 and HTTP
  errors are raised from the iterator.
- **STREAM-6**: Closing the iterator closes the vendor's response, complete or
  not. Callers that stop early close it (`contextlib.closing`, `aclosing`).

## Mapping

| | Anthropic | OpenRouter |
|---|---|---|
| Flag | `stream: true` | `stream: true` |
| Frames | `event:` + `data:` per message event | `data:` per chunk, `data: [DONE]` last, comment lines between |
| `TextDelta` | `text_delta` | `delta.content` |
| `ReasoningDelta` | `thinking_delta` | `delta.reasoning` |
| `ToolUseStart` | `content_block_start` of `tool_use` | The first `tool_calls` piece with an id and a name |
| `ToolUseDelta` | `input_json_delta` | `tool_calls[].function.arguments` |
| `ToolUseEnd` | `content_block_stop` | `finish_reason` |
| Complete | `message_stop` | `finish_reason` |
| Error | `event: error` | A chunk with `error` |
| Kept for `vendor` | Every block rebuilt, `signature_delta` and `citations_delta` included | `reasoning_details`, joined by `index` |

## Non-goals

- Events for the vendor's own tools (`ServerToolUseBlock`); they are in
  `Completed`.
- Usage before `Completed`.
- Reconnecting a cut stream.

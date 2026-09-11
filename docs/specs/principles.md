# Principles

Users should be able to instantiate the library client once.

The library should provide a synchronous client and an asynchronous client.

The client should expose methods for sending requests to different LLM vendors,
such as Anthropic, OpenAI, Gemini, or others.

One method of the client should receive as inputs:

- a provider/model following the LiteLLM convention, e.g. `"openai/gpt-4o"`
- a plain-text question (`str`)
- `web_search` (`bool`, default `False`)
- `reasoning` (`str`, from an enum)

That method should return a `str`.

The library internals should have a single abstract base class (ABC) that can be
implemented for each provider.

Each provider's code should live in a sub-directory.

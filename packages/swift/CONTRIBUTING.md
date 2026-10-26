# Contributing to the Swift port

See the [repository's CONTRIBUTING.md](../../CONTRIBUTING.md) first. Its
coverage rules apply here.

## Dependencies

The package depends on Foundation alone, so that it builds on every Apple
platform and on Linux. On Linux, `URLSession` comes from
`FoundationNetworking`.

## Checks

The same checks as CI, from this folder:

    swift format lint --recursive --strict Package.swift Sources Tests
    swift build --force-resolved-versions
    swift test --force-resolved-versions

`swift format format --recursive --in-place Package.swift Sources Tests` fixes
what the lint finds. Its settings are in `.swift-format`.

## Platforms

`URLSession` on Linux cuts a request's `timeoutInterval` to whole seconds, so
`URLSessionTransport` keeps the timeout of a call itself, and gives
`URLSession` a longer one as a backstop.

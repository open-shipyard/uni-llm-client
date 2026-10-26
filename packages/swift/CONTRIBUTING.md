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
    swift build
    swift test

`swift format format --recursive --in-place Package.swift Sources Tests` fixes
what the lint finds. Its settings are in `.swift-format`.

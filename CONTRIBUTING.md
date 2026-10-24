# Contributing to uni-llm-client

## Branching model

`main` is the only long-lived branch and must always be releasable. Direct
pushes to `main` are blocked.

1. Create a short-lived branch from `main` for each change, prefixed with
   `feature/` for new functionality or `fix/` for corrections:

       git switch main && git pull
       git switch -c feature/short-description

2. Open a pull request against `main`.
3. Once checks pass and review is complete, a maintainer merges it.

Releases are cut by maintainers by tagging a commit on `main` with a
[Semantic Versioning](https://semver.org/) tag such as `v0.2.0`. Fixes for a
release go through a regular pull request to `main` and ship in the next tag.

## Repository layout

Each port lives in `packages/<language>`. The language-agnostic tests live in
`tests`, and every port must pass them. A port joins them through its test
server, described in [tests/README.md](tests/README.md).

CI checks a package only when it changes. A change to `tests` runs the
language-agnostic tests of every package. A change to the CI workflow runs
everything. The `ci-ok` job passes when every other job passed or was skipped.

Each package has its own SonarQube Cloud project, set in its
`sonar-project.properties`. The root project covers `.github` and `tests`.
Coverage comes from the language-agnostic tests alone. The Python unit tests
report no coverage.

## Development setup

The Python port and the language-agnostic tests use
[uv](https://docs.astral.sh/uv/). Run the same checks as CI before opening a
pull request, in `packages/python` and in `tests`:

    uv sync
    uv run ruff check
    uv run ruff format --check
    uv run mypy
    uv run pytest

The TypeScript port uses npm. Installs are `npm ci`, never `npm install`:

    cd packages/typescript
    npm ci
    npm run typecheck

New source files start with the license header:

    # Copyright 2026 The uni-llm-client Authors
    # SPDX-License-Identifier: Apache-2.0

The Python package ships copies of `LICENSE`, `NOTICE` and `AUTHORS`. Edit the
files at the root, then copy them to `packages/python`.

## Developer Certificate of Origin

All contributions must be signed off under the
[Developer Certificate of Origin 1.1](https://developercertificate.org/).
Add `-s` to your commit:

    git commit -s -m "component: short imperative summary"

which appends:

    Signed-off-by: Jane Doe <jane@example.com>

Use your real name and a reachable email address. Sign-off is a statement about
the provenance of your contribution, so pseudonymous sign-offs cannot be
accepted. If you are contributing on behalf of an employer, make sure you have
their authorization.

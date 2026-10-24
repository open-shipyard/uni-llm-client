# Contributing to the Python port

See the [repository's CONTRIBUTING.md](../../CONTRIBUTING.md) first. Its
coverage rules apply here.

## Coverage

The test server in `tests/server.py` runs under coverage.py during the HTTP
tests. The unit tests in `packages/python/tests` run with plain `pytest`,
without `--cov` or `coverage run`.

SonarQube Cloud reads `coverage.xml`. To see the coverage locally:

    cd tests
    uv run pytest --package python
    cd ../packages/python
    uv run coverage combine
    uv run coverage report

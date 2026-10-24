# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial Python project structure.

### Changed

- The HTTP layer uses `httpx2` instead of `httpx`. An `http_client` passed to
  a client must be an `httpx2.Client` or `httpx2.AsyncClient`.

### Fixed

- Importing from a source checkout that is not installed no longer raises
  `PackageNotFoundError`; `__version__` is `"0+unknown"` there.

[Unreleased]: https://github.com/open-shipyard/uni-llm-client/commits/main

#!/usr/bin/env bash
# Run ruff linter and formatter check. Fails on any finding.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run ruff check .
uv run ruff format --check .

#!/usr/bin/env bash
# Run mypy type checker. Fails on any type error.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run mypy securehpc

#!/usr/bin/env bash
# Run the test suite. Extra arguments go to pytest, e.g. ./scripts/test.sh -k config
set -euo pipefail

cd "$(dirname "$0")/.."

uv run pytest "$@"

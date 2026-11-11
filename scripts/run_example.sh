#!/usr/bin/env bash
# Builds the example container (once) and submits example/run.toml.
# Extra arguments go to submit, e.g. ./scripts/run_example.sh --debug
set -euo pipefail
cd "$(dirname "$0")/../example"

# the default container.private_key from config.toml
key=~/.config/securehpc/rsa_pri.pem

if [ ! -f "$key" ]; then
    echo "Creating the container key $key"
    mkdir -p "$(dirname "$key")"
    ssh-keygen -q -t rsa -b 4096 -m pem -N "" -f "$key"  # private key is written with chmod 600
    rm "$key.pub"
fi

if [ ! -f container.sif ]; then
    echo "Building the encrypted container example/container.sif"
    pub=$(mktemp)
    ssh-keygen -e -m pem -f "$key" > "$pub"
    sudo apptainer build --pem-path="$pub" container.sif container.def
    rm "$pub"
fi

uv run securehpc submit run.toml "$@"

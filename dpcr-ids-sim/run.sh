#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$PROJECT_DIR/src"
SIM_DIR="$PROJECT_DIR/simulations"
EXE="$PROJECT_DIR/out/clang-release/src/dpcr-ids-sim"

if [ ! -f "$EXE" ]; then
    echo "ERROR: Executable not found. Build first from src/"
    exit 1
fi

mkdir -p "$SIM_DIR/results"

CONFIG="${1:-General}"
LIMIT="${2:-10s}"

echo "Running config: $CONFIG (limit=$LIMIT)"
cd "$SIM_DIR"
"$EXE" -u Cmdenv -n "$SRC_DIR" -f "$SIM_DIR/omnetpp.ini" -c "$CONFIG" --sim-time-limit="$LIMIT"
echo "Done."

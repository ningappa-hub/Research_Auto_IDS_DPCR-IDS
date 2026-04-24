#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$PROJECT_DIR/src"
SIM_DIR="$PROJECT_DIR/simulations"
ONNX_LIB_DIR="$PROJECT_DIR/onnxruntime-linux-x64-1.17.0/lib"

EXE=""
for candidate in \
    "$PROJECT_DIR/out/clang-release/src/dpcr-ids-sim" \
    "$PROJECT_DIR/src/dpcr-ids-sim" \
    "$PROJECT_DIR/out/clang-release/simulations/dpcr-ids-sim" \
    "$PROJECT_DIR/simulations/dpcr-ids-sim"; do
    if [ -f "$candidate" ]; then
        EXE="$candidate"
        break
    fi
done

if [ -z "$EXE" ]; then
    echo "ERROR: DPCR-IDS simulation executable not found. Build first:"
    echo "  bash ./visual_quickstart.sh General 5s"
    exit 1
fi

if [ -d "$ONNX_LIB_DIR" ]; then
    export LD_LIBRARY_PATH="$ONNX_LIB_DIR:${LD_LIBRARY_PATH:-}"
fi

mkdir -p "$SIM_DIR/results"

CONFIG="${1:-General}"
LIMIT="${2:-10s}"

echo "Running config: $CONFIG (limit=$LIMIT)"
echo "Project: $PROJECT_DIR"
echo "Executable: $EXE"
cd "$SIM_DIR"
"$EXE" -u Cmdenv -n "$SRC_DIR" -f "$SIM_DIR/omnetpp.ini" -c "$CONFIG" --sim-time-limit="$LIMIT"
echo "Done."

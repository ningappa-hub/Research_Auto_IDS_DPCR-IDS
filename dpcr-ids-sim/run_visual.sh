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
    echo "ERROR: DPCR-IDS simulation executable not found."
    echo "Project directory detected as: $PROJECT_DIR"
    echo ""
    echo "Build the simulation first from the project directory:"
    echo "  cd $PROJECT_DIR"
    echo "  bash ./build.sh --with-onnx"
    echo ""
    echo "If you are inside ~/default_workspace/omnetpp-6.3.0, you are in the OMNeT++"
    echo "installation folder, not the dpcr-ids-sim project folder."
    exit 1
fi

if [ -d "$ONNX_LIB_DIR" ]; then
    export LD_LIBRARY_PATH="$ONNX_LIB_DIR:${LD_LIBRARY_PATH:-}"
fi

mkdir -p "$SIM_DIR/results"

CONFIG="${1:-MultiAttack}"
LIMIT="${2:-25s}"

echo "Running visual config: $CONFIG (limit=$LIMIT)"
echo "Project: $PROJECT_DIR"
echo "Executable: $EXE"
echo ""
echo "Qtenv opens paused. In the Qtenv window, click Run/Fast/Express"
echo "and let the simulation pass the attack start time. Closing Qtenv"
echo "before pressing Run creates empty .vec/.csv result files."
echo ""
cd "$SIM_DIR"
"$EXE" -u Qtenv -n "$SRC_DIR" -f "$SIM_DIR/omnetpp.ini" -c "$CONFIG" --sim-time-limit="$LIMIT"
echo "Done."

#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${1:-MultiAttack}"
LIMIT="${2:-25s}"
ONNX_DIR="$PROJECT_DIR/onnxruntime-linux-x64-1.17.0"

echo "DPCR-IDS visual quickstart"
echo "Project: $PROJECT_DIR"

if [ ! -f "$PROJECT_DIR/src/AutomotiveNetwork.ned" ]; then
    echo "ERROR: This does not look like the dpcr-ids-sim project directory."
    exit 1
fi

if ! command -v opp_makemake >/dev/null 2>&1; then
    echo "ERROR: OMNeT++ tools are not on PATH."
    echo ""
    echo "Open an OMNeT++ shell first. If your prompt already starts with"
    echo "'omnetpp-6.3.0:', do not run opp_env shell again."
    echo ""
    echo "Example:"
    echo "  opp_env shell omnetpp-6.3.0"
    echo "  cd $PROJECT_DIR"
    echo "  bash ./visual_quickstart.sh $CONFIG $LIMIT"
    exit 1
fi

if [ -d "$ONNX_DIR" ]; then
    export ONNX_RUNTIME_DIR="$ONNX_DIR"
    export LD_LIBRARY_PATH="$ONNX_DIR/lib:${LD_LIBRARY_PATH:-}"
fi

EXE_FOUND=false
EXE_PATH=""
for candidate in \
    "$PROJECT_DIR/out/clang-release/src/dpcr-ids-sim" \
    "$PROJECT_DIR/src/dpcr-ids-sim" \
    "$PROJECT_DIR/out/clang-release/simulations/dpcr-ids-sim" \
    "$PROJECT_DIR/simulations/dpcr-ids-sim"; do
    if [ -f "$candidate" ]; then
        EXE_FOUND=true
        EXE_PATH="$candidate"
        break
    fi
done

NEEDS_BUILD=false
if [ "$EXE_FOUND" = false ]; then
    NEEDS_BUILD=true
    echo "Simulation executable not found; building dpcr-ids-sim now."
elif find "$PROJECT_DIR/src" -type f \( -name "*.cc" -o -name "*.h" -o -name "*.ned" -o -name "*.msg" \) -newer "$EXE_PATH" | grep -q .; then
    NEEDS_BUILD=true
    echo "Simulation source is newer than executable; rebuilding dpcr-ids-sim."
fi

if [ "$NEEDS_BUILD" = true ]; then
    if [ -f "$ONNX_DIR/lib/libonnxruntime.so" ]; then
        bash "$PROJECT_DIR/build.sh" --with-onnx
    else
        echo "ONNX Runtime library not found; building in stub mode."
        bash "$PROJECT_DIR/build.sh"
    fi
fi

bash "$PROJECT_DIR/run_visual.sh" "$CONFIG" "$LIMIT"

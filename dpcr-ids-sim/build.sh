#!/bin/bash
# ===========================================================================
# build.sh — Build script for DPCR-IDS OMNeT++ Simulation
#
# Usage (inside opp_env shell):
#   ./build.sh              — build in STUB mode (no ONNX Runtime needed)
#   ./build.sh --with-onnx  — build with ONNX Runtime (full inference)
#   ./build.sh clean        — clean build artifacts
#
# The STUB mode generates synthetic model outputs from input statistics,
# allowing you to validate the simulation framework (topology, traffic,
# routing, aggregation) without needing ONNX Runtime installed.
# ===========================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$PROJECT_DIR/src"
SIM_DIR="$PROJECT_DIR/simulations"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# --- Parse arguments ---
USE_ONNX=false
CLEAN=false
for arg in "$@"; do
    case $arg in
        --with-onnx) USE_ONNX=true ;;
        clean)       CLEAN=true ;;
        *)           echo -e "${RED}Unknown argument: $arg${NC}"; exit 1 ;;
    esac
done

# --- Clean ---
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Cleaning build artifacts...${NC}"
    cd "$SRC_DIR"
    make clean 2>/dev/null || true
    rm -rf out Makefile
    echo -e "${GREEN}Clean complete.${NC}"
    exit 0
fi

# --- Check OMNeT++ ---
if ! command -v opp_makemake &>/dev/null; then
    echo -e "${RED}ERROR: opp_makemake not found. Are you inside an opp_env shell?${NC}"
    echo "Run: opp_env shell omnetpp-6.3.0"
    exit 1
fi

echo -e "${GREEN}OMNeT++ found: $(opp_makemake --version 2>&1 | head -1)${NC}"

# --- Build ONNX flags ---
EXTRA_CFLAGS=""
EXTRA_LDFLAGS=""
EXTRA_INCLUDES=""

if [ "$USE_ONNX" = true ]; then
    echo -e "${GREEN}Building with ONNX Runtime (full inference mode)${NC}"

    # Look for ONNX Runtime
    if [ -n "$ONNX_RUNTIME_DIR" ] && [ -d "$ONNX_RUNTIME_DIR" ]; then
        echo "  ONNX Runtime dir: $ONNX_RUNTIME_DIR"
        EXTRA_INCLUDES="-I$ONNX_RUNTIME_DIR/include"
        EXTRA_LDFLAGS="-L$ONNX_RUNTIME_DIR/lib -lonnxruntime"
    else
        echo -e "${RED}ERROR: ONNX_RUNTIME_DIR not set or not found.${NC}"
        echo "Install ONNX Runtime:"
        echo "  wget https://github.com/microsoft/onnxruntime/releases/download/v1.17.0/onnxruntime-linux-x64-1.17.0.tgz"
        echo "  tar xzf onnxruntime-linux-x64-1.17.0.tgz"
        echo "  export ONNX_RUNTIME_DIR=\$(pwd)/onnxruntime-linux-x64-1.17.0"
        exit 1
    fi
else
    echo -e "${YELLOW}Building in STUB mode (no ONNX Runtime — synthetic outputs)${NC}"
    EXTRA_CFLAGS="-DDPCR_NO_ONNX"
fi

# --- Generate Makefiles ---
echo ""
echo -e "${GREEN}Generating Makefiles...${NC}"
cd "$SRC_DIR"

opp_makemake -f --deep \
    -O out \
    -o dpcr-ids-sim \
    $EXTRA_INCLUDES \
    --msg6 \
    -X out

# --- Inject custom CFLAGS/LDFLAGS into generated Makefile ---
if [ -n "$EXTRA_CFLAGS" ]; then
    echo "CFLAGS += $EXTRA_CFLAGS" >> Makefile
fi
if [ -n "$EXTRA_LDFLAGS" ]; then
    echo "LDFLAGS += $EXTRA_LDFLAGS" >> Makefile
fi

# --- Build ---
echo ""
echo -e "${GREEN}Compiling...${NC}"
make -j$(nproc) MODE=release 2>&1

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$USE_ONNX" = true ]; then
    echo "Mode: ONNX Runtime (real inference)"
    echo "Make sure LD_LIBRARY_PATH includes: $ONNX_RUNTIME_DIR/lib"
else
    echo "Mode: STUB (synthetic outputs for validation)"
    echo "To use real ONNX inference, rebuild with: ./build.sh --with-onnx"
fi

echo ""
echo "To run:"
echo "  cd $SIM_DIR"
echo "  opp_run -n ../src:. -l ../src/out/gcc-release/src/libdpcr-ids-sim omnetpp.ini"
echo ""
echo "Or with Qtenv GUI:"
echo "  opp_run -n ../src:. -l ../src/out/gcc-release/src/libdpcr-ids-sim omnetpp.ini -u Qtenv"

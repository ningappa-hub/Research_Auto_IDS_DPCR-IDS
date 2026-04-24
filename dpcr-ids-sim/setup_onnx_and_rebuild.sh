#!/bin/bash
# ===========================================================================
# setup_onnx_and_rebuild.sh — Rebuild with real ONNX Runtime models
# ONNX Runtime already downloaded to project directory.
# Run inside opp_env: bash ./setup_onnx_and_rebuild.sh
# ===========================================================================

set -e

PROJECT="$(cd "$(dirname "$0")" && pwd)"
ONNX_DIR="$PROJECT/onnxruntime-linux-x64-1.17.0"

echo "============================================"
echo "  Step 1: Verify ONNX Runtime"
echo "============================================"

if [ ! -f "$ONNX_DIR/lib/libonnxruntime.so" ]; then
    echo "ERROR: ONNX Runtime not found at $ONNX_DIR"
    exit 1
fi
echo "  [OK] ONNX Runtime found at $ONNX_DIR"

export ONNX_RUNTIME_DIR="$ONNX_DIR"
export LD_LIBRARY_PATH="$ONNX_DIR/lib:${LD_LIBRARY_PATH:-}"

echo ""
echo "============================================"
echo "  Step 2: Rebuild with real ONNX inference"
echo "============================================"

cd "$PROJECT/src"
make clean 2>/dev/null || true

opp_makemake -f --deep \
    -O out \
    -o dpcr-ids-sim \
    -I"$ONNX_DIR/include" \
    -L"$ONNX_DIR/lib" \
    -lonnxruntime \
    -X out

make -j$(nproc) MODE=release

echo ""
echo "============================================"
echo "  Step 3: Verify ONNX models"
echo "============================================"

for model in can_student.onnx eth_student.onnx fusion_student.onnx; do
    if [ -f "$PROJECT/simulations/models/$model" ]; then
        size=$(stat -c%s "$PROJECT/simulations/models/$model" 2>/dev/null || echo "?")
        echo "  [OK] $model ($size bytes)"
    else
        echo "  [MISSING] $model"
    fi
done

echo ""
echo "============================================"
echo "  Step 4: Quick test (General, 5s)"
echo "============================================"

cd "$PROJECT/simulations"
rm -f results/*.sca results/*.vec results/*.vci results/*.csv 2>/dev/null

"$PROJECT/out/clang-release/src/dpcr-ids-sim" \
    -u Cmdenv -n ../src -f omnetpp.ini \
    -c General --sim-time-limit=5s

echo ""
echo "============================================"
echo "  Done! Real ONNX inference active."
echo "============================================"
echo ""
echo "Run all scenarios: bash $PROJECT/run_all_scenarios.sh"
echo ""
echo "IMPORTANT: Before every opp_env session, run:"
echo "  export LD_LIBRARY_PATH=$ONNX_DIR/lib:\$LD_LIBRARY_PATH"

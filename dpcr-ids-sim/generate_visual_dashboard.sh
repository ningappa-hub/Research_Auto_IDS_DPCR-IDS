#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "$PROJECT_DIR/tools/visual_dashboard.py" \
    --results-dir "$PROJECT_DIR/simulations/results" \
    --output "$PROJECT_DIR/simulations/results/visual_dashboard.html" \
    "$@"

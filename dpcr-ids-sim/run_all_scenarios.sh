#!/bin/bash
# ===========================================================================
# run_all_scenarios.sh — Run ALL DPCR-IDS simulation scenarios
# Paste the contents of this file into your opp_env terminal, or:
#   bash /c/ResearchAutoIDS/dpcr-ids-sim/run_all_scenarios.sh
# ===========================================================================

set -e

SIM_DIR="/c/ResearchAutoIDS/dpcr-ids-sim/simulations"
EXE="/c/ResearchAutoIDS/dpcr-ids-sim/out/clang-release/src/dpcr-ids-sim"

cd "$SIM_DIR"
mkdir -p results

echo "============================================"
echo "  DPCR-IDS: Running ALL Simulation Scenarios"
echo "============================================"

run() {
    CONFIG="$1"
    LIMIT="$2"
    echo ""
    echo "--- [$CONFIG] sim-time=$LIMIT ---"
    "$EXE" -u Cmdenv -n ../src -f omnetpp.ini -c "$CONFIG" --sim-time-limit="$LIMIT" 2>&1 | grep -E '(Event #|Simulation time limit|Run statistics|Error)'
    echo "    [$CONFIG] Done."
}

# Attack scenarios
run "Fuzzy"       "20s"
run "GearSpoof"   "20s"
run "RpmSpoof"    "20s"
run "MultiAttack" "25s"

# Bus load sweep
run "BusLoadLow"  "20s"
run "BusLoadMed"  "20s"
run "BusLoadHigh" "20s"

# Scaling sweep
run "ScaleSmall"  "20s"
run "ScaleMedium" "20s"
run "ScaleLarge"  "20s"

echo ""
echo "============================================"
echo "  ALL SCENARIOS COMPLETE"
echo "============================================"
echo ""
echo "Results in: $SIM_DIR/results/"
ls -la "$SIM_DIR/results/"*.sca 2>/dev/null | wc -l
echo " .sca files generated."
ls -la "$SIM_DIR/results/"*.csv 2>/dev/null
echo ""
echo "Next: Run analysis on Windows:"
echo "  .venv\\Scripts\\python.exe analyze_simulation_results.py"

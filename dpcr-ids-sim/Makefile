#
# Makefile for DPCR-IDS OMNeT++ Simulation
#
# Prerequisites:
#   - OMNeT++ 6.3.0 (sourced via opp_env)
#   - ONNX Runtime C++ (linked below)
#
# Usage:
#   make makefiles   — generate Makefiles via opp_makemake
#   make             — build the simulation
#   make clean       — clean build artifacts
#

# ONNX Runtime paths (adjust to your installation)
ONNX_RUNTIME_DIR ?= /opt/onnxruntime
ONNX_INCLUDE = $(ONNX_RUNTIME_DIR)/include
ONNX_LIB = $(ONNX_RUNTIME_DIR)/lib

.PHONY: all makefiles clean run run-visual visual-quickstart dashboard

all: makefiles
	$(MAKE) -C src

makefiles:
	cd src && opp_makemake -f --deep \
		-O out \
		-I$(ONNX_INCLUDE) \
		-L$(ONNX_LIB) \
		-lonnxruntime

clean:
	cd src && $(MAKE) clean 2>/dev/null; true
	rm -rf src/out

# Run the default (General) configuration
run:
	cd simulations && ../src/out/gcc-release/src/dpcr-ids-sim \
		-u Cmdenv -n ../src:. omnetpp.ini

# Run a specific config
run-%:
	cd simulations && ../src/out/gcc-release/src/dpcr-ids-sim \
		-u Cmdenv -c $* -n ../src:. omnetpp.ini

# Run all attack scenarios
run-attacks: run-DoS run-Fuzzy run-GearSpoof run-RpmSpoof run-MultiAttack

# Run all bus load sweep
run-busload: run-BusLoadLow run-BusLoadMed run-BusLoadHigh

# Run all scaling experiments
run-scale: run-ScaleSmall run-ScaleMedium run-ScaleLarge

# Run ALL experiments
run-all: run run-attacks run-busload run-scale

# Launch Qtenv visual mode without changing the existing Cmdenv run path.
run-visual:
	bash ./run_visual.sh MultiAttack 25s

# Build if needed, then launch Qtenv visual mode.
visual-quickstart:
	bash ./visual_quickstart.sh MultiAttack 25s

# Build a browser-readable dashboard from existing alert CSV logs.
dashboard:
	bash ./generate_visual_dashboard.sh

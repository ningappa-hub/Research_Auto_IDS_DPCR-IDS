# DPCR-IDS OMNeT++ Simulation

Discrete-event network simulation of the **DPCR-IDS** (Dual-Protocol Cascade Routing Intrusion Detection System) for automotive CAN + Ethernet networks. This simulation validates the late-fusion architecture under realistic bus timing, multi-ECU topologies, and configurable attack scenarios.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AutomotiveNetwork                             │
│                                                                  │
│  ┌──────────┐  ┌──────────┐       ┌──────────────────────────┐  │
│  │ Sensor   │  │ Attacker │       │    Gateway ECU (IDS)     │  │
│  │ ECU ×N   │  │ ECU(s)   │       │                          │  │
│  │(CAN Gen) │  │(DoS/Fuzz/│  CAN  │ ┌────────┐  ┌────────┐  │  │
│  └────┬─────┘  │ Spoof)   │──────▶│ │CAN     │  │Fusion  │  │  │
│       │        └────┬─────┘       │ │Expert  ├─▶│IDS     │  │  │
│       │             │             │ │(ONNX)  │  │(ONNX)  │  │  │
│       └─────────────┘             │ └────────┘  └───┬────┘  │  │
│                                   │                  │       │  │
│  ┌──────────┐                     │ ┌────────┐  ┌───▼────┐  │  │
│  │ ADAS     │             ETH     │ │ETH     │  │Router  │  │  │
│  │ ECU ×M   │────────────────────▶│ │Expert  ├─▶│(τ_low/ │  │  │
│  │(Eth Gen) │                     │ │(ONNX)  │  │ τ_high)│  │  │
│  └──────────┘                     │ └────────┘  └───┬────┘  │  │
│                                   │                  │       │  │
│                                   │            ┌─────▼─────┐ │  │
│                                   │            │Aggregator │ │  │
│                                   │            │(250ms     │─┼─▶ AlertSink
│                                   │            │ buckets)  │ │  │
│                                   │            └───────────┘ │  │
│                                   └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **OMNeT++ 6.3.0** (via `opp_env`)
2. **ONNX Runtime** C++ shared library (≥1.16):
   ```bash
   # Download pre-built release
   wget https://github.com/microsoft/onnxruntime/releases/download/v1.17.0/onnxruntime-linux-x64-1.17.0.tgz
   tar xzf onnxruntime-linux-x64-1.17.0.tgz
   export ONNX_RUNTIME_DIR=$(pwd)/onnxruntime-linux-x64-1.17.0
   ```
3. **ONNX Model Files** — place in `simulations/models/`:
   - `can_student.onnx`
   - `eth_student.onnx`
   - `fusion_student.onnx`

## Building

```bash
# Enter OMNeT++ environment
opp_env shell

# Build the simulation
cd dpcr-ids-sim
make makefiles
make -j$(nproc)
```

## Running Simulations

```bash
# Run baseline (no attacks)
make run

# Run specific attack scenario
make run-DoS
make run-Fuzzy
make run-GearSpoof
make run-RpmSpoof
make run-MultiAttack

# Run bus load sweep
make run-busload

# Run ECU scaling experiments
make run-scale

# Run ALL experiments
make run-all
```

## Simulation Configurations

| Config | Description | Attack | Duration |
|--------|-------------|--------|----------|
| `General` | Baseline — no attacks | None | 30s |
| `DoS` | CAN DoS flood (10k msg/s) | DoS | 10s window |
| `Fuzzy` | Random CAN ID/payload injection | Fuzzy | 10s window |
| `GearSpoof` | Gear control masquerade | Spoof | 10s window |
| `RpmSpoof` | RPM sensor masquerade | Spoof | 10s window |
| `MultiAttack` | Sequential DoS → Fuzzy → Spoof | All | 25s |
| `BusLoadLow` | 2 sensor ECUs (~20% load) | DoS | 10s window |
| `BusLoadMed` | 8 sensor ECUs (~50% load) | DoS | 10s window |
| `BusLoadHigh` | 15 sensor ECUs (~80% load) | DoS | 10s window |
| `ScaleSmall` | 3+2 ECUs (5 total) | Fuzzy | 10s window |
| `ScaleMedium` | 7+3 ECUs (10 total) | Fuzzy | 10s window |
| `ScaleLarge` | 15+5 ECUs (20 total) | Fuzzy | 10s window |

## IDS Parameters (matching Python pipeline)

| Parameter | Value | Source |
|-----------|-------|--------|
| CAN window size | 100 frames | `research_pipeline.yaml` |
| CAN stride | 50 | `research_pipeline.yaml` |
| CAN features | 16 | `research_pipeline.yaml` |
| CAN temperature | 0.95 | `calibration/can.json` |
| ETH image shape | [3, 32, 32] | `research_pipeline.yaml` |
| ETH temperature | 0.5 | `calibration/ethernet.json` |
| Fusion input | [2, 129] | `research_pipeline.yaml` |
| Fusion temperature | 1.1 | `calibration/fusion.json` |
| Router τ_low | 0.15 | `research_pipeline.yaml` |
| Router τ_high | 0.85 | `research_pipeline.yaml` |
| Aggregator bucket | 250ms | `research_pipeline.yaml` |

## Output

Results are written to `simulations/results/`:
- **Scalar files** (`.sca`): per-run summary statistics
- **Vector files** (`.vec`): time-series data for every signal
- **CSV logs**: per-alert decision logs
- **Event logs** (`.elog`): full simulation traces for the OMNeT++ IDE

## Project Structure

```
dpcr-ids-sim/
├── Makefile
├── package.ned
├── .project
├── .nedfolders
├── src/
│   ├── ids/                      # IDS pipeline modules
│   │   ├── CanExpertIDS.*        # CAN TCN expert
│   │   ├── EthExpertIDS.*        # Ethernet CNN expert
│   │   ├── FusionIDS.*           # Late fusion head
│   │   ├── ConfidenceRouter.*    # τ-threshold routing
│   │   └── DecisionAggregator.*  # Time-bucket merging
│   ├── traffic/                  # Traffic generators
│   │   ├── CanTrafficGen.*       # Normal CAN sensor ECU
│   │   ├── EthTrafficGen.*       # Normal Ethernet ADAS ECU
│   │   ├── Attackers.ned         # Attack module NED defs
│   │   ├── DosAttacker.cc        # DoS flood attack
│   │   ├── FuzzyAttacker.cc      # Fuzzy injection attack
│   │   └── SpoofAttacker.cc      # Gear/RPM masquerade
│   ├── nodes/                    # Compound network nodes
│   │   ├── GatewayNode.ned       # Gateway ECU (IDS host)
│   │   ├── AlertSink.*           # Result collection
│   ├── msg/                      # Message definitions
│   │   ├── CanFrameMsg.msg
│   │   ├── EthFrameMsg.msg
│   │   ├── ExpertOutput.msg
│   │   ├── FusionResult.msg
│   │   └── AlertMsg.msg
│   └── utils/                    # Utility classes
│       ├── OnnxInference.*       # ONNX Runtime wrapper
│       ├── FeatureExtractor.h    # CAN 16-feature extraction
│       └── TemperatureScaler.h   # Calibration
└── simulations/
    ├── AutomotiveNetwork.ned     # Network topology
    ├── omnetpp.ini               # All simulation configs
    └── models/                   # ONNX model files (place here)
        ├── can_student.onnx
        ├── eth_student.onnx
        └── fusion_student.onnx
```

## Extending with INET / FiCo4OMNeT

For full-fidelity simulation with realistic CAN arbitration and Ethernet TSN:

1. Install **FiCo4OMNeT** for CAN bus arbitration:
   ```bash
   git clone https://github.com/CoRE-RG/FiCo4OMNeT.git
   ```
2. Install **INET 4.x** for Ethernet switches and TSN:
   ```bash
   git clone https://github.com/inet-framework/inet.git
   ```
3. Install **SignalsAndGateways** for CAN↔Ethernet gateway:
   ```bash
   git clone https://github.com/CoRE-RG/SignalsAndGateways.git
   ```
4. Replace direct connections in `AutomotiveNetwork.ned` with FiCo4OMNeT `CanBus` and INET `EthernetSwitch` modules.

// --------------------------------------------------------------------------
// AutomotiveNetwork.ned — Full vehicle network topology for IDS simulation.
//
// Topology:
//   - Multiple Sensor ECUs generating normal CAN traffic
//   - ADAS ECU generating normal Ethernet traffic
//   - Attacker ECU(s) injecting malicious CAN frames
//   - Central Gateway ECU with embedded DPCR-IDS pipeline
//   - Alert Sink for results collection
//
// Architecture Note:
//   - CAN nodes connect via a CanBusHub that merges all CAN frames
//   - Ethernet nodes connect via an EthBusHub that merges Ethernet frames
//   - Gateway receives merged streams and runs the IDS pipeline
// --------------------------------------------------------------------------

package dpcrids;

import dpcrids.traffic.CanTrafficGen;
import dpcrids.traffic.EthTrafficGen;
import dpcrids.traffic.DosAttacker;
import dpcrids.traffic.FuzzyAttacker;
import dpcrids.traffic.SpoofAttacker;
import dpcrids.nodes.GatewayNode;
import dpcrids.nodes.AlertSink;
import dpcrids.nodes.CanBusHub;
import dpcrids.nodes.EthBusHub;

//
// AutomotiveNetwork: A configurable in-vehicle network with IDS.
//
network AutomotiveNetwork
{
    parameters:
        int numSensorECUs = default(5);
        int numAdasECUs = default(2);
        bool enableDos = default(false);
        bool enableFuzzy = default(false);
        bool enableSpoof = default(false);
        @display("bgb=900,700");

    submodules:
        // Normal CAN traffic generators (sensor ECUs)
        sensor[numSensorECUs]: CanTrafficGen {
            parameters:
                startCanId = 0x100 + index * 10;
                @display("p=80,80+70*index");
        }

        // Normal Ethernet traffic generators (ADAS ECUs)
        adas[numAdasECUs]: EthTrafficGen {
            @display("p=80,550+70*index");
        }

        // Attack modules (conditionally active)
        dosAttacker: DosAttacker if enableDos {
            @display("p=250,50");
        }
        fuzzyAttacker: FuzzyAttacker if enableFuzzy {
            @display("p=250,140");
        }
        spoofAttacker: SpoofAttacker if enableSpoof {
            @display("p=250,230");
        }

        // Bus hubs (merge multiple sources into single stream)
        canHub: CanBusHub {
            parameters:
                // Total CAN gates = numSensorECUs + up to 3 attackers
                numInputs = parent.numSensorECUs
                            + (parent.enableDos ? 1 : 0)
                            + (parent.enableFuzzy ? 1 : 0)
                            + (parent.enableSpoof ? 1 : 0);
                @display("p=400,200");
        }

        ethHub: EthBusHub {
            parameters:
                numInputs = parent.numAdasECUs;
                @display("p=400,550");
        }

        // Central gateway with embedded IDS
        gateway: GatewayNode {
            @display("p=580,380");
        }

        // Alert collection sink
        alertSink: AlertSink {
            @display("p=760,380");
        }

    connections allowunconnected:
        // Sensor ECUs → CAN bus hub
        for i=0..numSensorECUs-1 {
            sensor[i].canOut --> canHub.in[i];
        }

        // Attacker ECUs → CAN bus hub (after sensor gates)
        dosAttacker.canOut --> canHub.in[numSensorECUs] if enableDos;
        fuzzyAttacker.canOut --> canHub.in[numSensorECUs + (enableDos ? 1 : 0)] if enableFuzzy;
        spoofAttacker.canOut --> canHub.in[numSensorECUs + (enableDos ? 1 : 0) + (enableFuzzy ? 1 : 0)] if enableSpoof;

        // ADAS ECUs → Ethernet bus hub
        for i=0..numAdasECUs-1 {
            adas[i].ethOut --> ethHub.in[i];
        }

        // Bus hubs → Gateway
        canHub.out --> gateway.canBusIn;
        ethHub.out --> gateway.ethBusIn;

        // Gateway alerts → Sink
        gateway.gatewayAlertOut --> alertSink.alertIn;
}

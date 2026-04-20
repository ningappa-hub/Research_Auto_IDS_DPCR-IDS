// --------------------------------------------------------------------------
// GatewayNode.ned — Compound module: central gateway ECU with IDS pipeline.
// This is the core node that houses all IDS modules.
// --------------------------------------------------------------------------

package dpcrids.nodes;

import dpcrids.ids.CanExpertIDS;
import dpcrids.ids.EthExpertIDS;
import dpcrids.ids.FusionIDS;
import dpcrids.ids.ConfidenceRouter;
import dpcrids.ids.DecisionAggregator;

//
// GatewayNode: Central gateway ECU bridging CAN and Ethernet domains.
// Contains the full DPCR-IDS pipeline: CAN Expert → Fusion ← Eth Expert → Router → Aggregator
//
module GatewayNode
{
    parameters:
        @display("i=device/server2,gold;bgb=600,400");

    gates:
        input canBusIn;
        input ethBusIn;
        output gatewayAlertOut;

    submodules:
        canExpert: CanExpertIDS {
            @display("p=100,100");
        }
        ethExpert: EthExpertIDS {
            @display("p=100,300");
        }
        fusion: FusionIDS {
            @display("p=250,200");
        }
        router: ConfidenceRouter {
            @display("p=400,200");
        }
        aggregator: DecisionAggregator {
            @display("p=550,200");
        }

    connections:
        canBusIn --> canExpert.canFrameIn;
        ethBusIn --> ethExpert.ethFrameIn;
        canExpert.expertOut --> fusion.canExpertIn;
        ethExpert.expertOut --> fusion.ethExpertIn;
        fusion.fusionOut --> router.fusionIn;
        router.decisionOut --> aggregator.alertIn;
        aggregator.gatewayOut --> gatewayAlertOut;
}

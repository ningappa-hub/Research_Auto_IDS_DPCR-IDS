// --------------------------------------------------------------------------
// ConfidenceRouter.ned — Two-threshold fast/heavy path routing.
// --------------------------------------------------------------------------

package dpcrids.ids;

simple ConfidenceRouter
{
    parameters:
        double tauLow = default(0.15);
        double tauHigh = default(0.85);
        double fallbackUncertaintyLow = default(0.3);
        double fallbackUncertaintyHigh = default(0.7);
        bool expertOverride = default(true);   // Expert-aware joint-normal override
        @display("i=block/routing,orange");
        @signal[routeDecision](type=long);       // 0=NORMAL, 1=ATTACK, 2=ESCALATE
        @signal[routePath](type=long);            // 0=fast, 1=heavy, 2=fail_open
        @signal[routingLatencyMs](type=double);
        @statistic[routeDecision](record=vector,histogram);
        @statistic[routePath](record=vector,histogram);
        @statistic[routingLatencyMs](record=vector,mean,max);

    gates:
        input fusionIn;        // FusionResult from FusionIDS
        output decisionOut;    // Routed alert to DecisionAggregator
}


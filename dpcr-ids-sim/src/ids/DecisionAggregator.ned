// --------------------------------------------------------------------------
// DecisionAggregator.ned — Gateway-level time-bucket decision merging.
// --------------------------------------------------------------------------

package dpcrids.ids;

simple DecisionAggregator
{
    parameters:
        double bucketMs = default(250);     // time window for merging alerts
        bool failOpen = default(true);      // fail-open safety behavior
        @display("i=block/table,purple");
        @signal[aggregatedDecision](type=long);
        @signal[bucketSize](type=long);
        @signal[endToEndLatencyMs](type=double);
        @statistic[aggregatedDecision](record=vector,histogram);
        @statistic[bucketSize](record=vector,mean,max);
        @statistic[endToEndLatencyMs](record=vector,mean,max,histogram);

    gates:
        input alertIn;          // AlertMsg from ConfidenceRouter
        output gatewayOut;      // merged gateway-level alerts
}

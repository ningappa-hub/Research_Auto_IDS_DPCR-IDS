// --------------------------------------------------------------------------
// AlertSink.ned — Sink module to collect and log gateway-level IDS alerts.
// --------------------------------------------------------------------------

package dpcrids.nodes;

simple AlertSink
{
    parameters:
        string logFile = default("results/ids_alerts.csv");
        @display("i=block/sink,grey");
        @signal[alertDecision](type=long);
        @signal[alertLatencyMs](type=double);
        @statistic[alertDecision](record=vector,histogram);
        @statistic[alertLatencyMs](record=vector,mean,max,histogram);

    gates:
        input alertIn;
}

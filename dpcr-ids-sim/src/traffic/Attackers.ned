// --------------------------------------------------------------------------
// Attackers.ned — Attack traffic generators for IDS validation.
// --------------------------------------------------------------------------

package dpcrids.traffic;

//
// DoS Attacker: floods the CAN bus with high-frequency frames.
//
simple DosAttacker
{
    parameters:
        double attackInterval @unit(s) = default(0.0001s);  // 10x normal rate
        double attackStartTime @unit(s) = default(2s);
        double attackDuration @unit(s) = default(5s);
        int targetCanId = default(0x000);        // DoS uses ID 0x000 for priority
        @display("i=block/source,red");
    gates:
        output canOut;
}

//
// Fuzzy Attacker: injects frames with random CAN IDs and payloads.
//
simple FuzzyAttacker
{
    parameters:
        double attackInterval @unit(s) = default(0.0005s);
        double attackStartTime @unit(s) = default(2s);
        double attackDuration @unit(s) = default(5s);
        @display("i=block/source,yellow");
    gates:
        output canOut;
}

//
// Spoof Attacker: masquerades as a specific ECU (gear/RPM spoofing).
//
simple SpoofAttacker
{
    parameters:
        double attackInterval @unit(s) = default(0.002s);   // same rate as victim
        double attackStartTime @unit(s) = default(2s);
        double attackDuration @unit(s) = default(5s);
        int spoofCanId = default(0x316);         // target CAN ID to impersonate
        string spoofType = default("gear");      // "gear" or "rpm"
        @display("i=block/source,magenta");
    gates:
        output canOut;
}

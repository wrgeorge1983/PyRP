next up:
All routing update messages are sent from port 520.
    Unsolicited routing update messages have both the source and
        destination port equal to 520.
    Those sent in response to a request
        are sent to the port from which the request came.

Specific queries and debugging requests may be sent from ports other than 520, but
they are directed to port 520 on the target machine.

Each route sent by a gateway
supercedes any previous route to the same destination from the same
gateway.

The timers are not right yet. there's whole parts of that we're not doing yet
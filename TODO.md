next up:


Specific queries and debugging requests may be sent from ports other than 520, but
they are directed to port 520 on the target machine.

Each route sent by a gateway
supercedes any previous route to the same destination from the same
gateway.




# full routing update lifecycle
* Protocol learns/updates a route from something other than redistribution, should trigger redistribution
* CP Rredistribution endpoint should include (optional) source protocol, if present
    ensures that we don't push updates back to originating protocol
* I feel like we require locks at this point to ensure protocol doesn't have to juggle (near) simultaneous updates from 
    CP and neighboring routers


# Timing
* The timers are not right yet. there's whole parts of that we're not doing yet

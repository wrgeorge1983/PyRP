# RIPv1

## Gaps from the RFC
* 'request' messages can either request the entire routing table or a subset of it. We only support the entire routing table
* split horizon is not implemented (but we only have 1 interface, so reflecting updates
    out the same interface is the only way we can see the router doing anything).
* poisoned reverse is not implemented 
* triggered updates are only implemented for max metric updates

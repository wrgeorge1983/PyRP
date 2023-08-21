rib as an instance or sublcass of something more generic.

RIB/FIB/internal data structures/etc all peers derived from a common base class.

pbasic needs:

 - configured_route store (which is just the rib?)
 - configured_routes have:
   - prefix
   - next_hop
   - priority (higher wins for selection)
   - status (up/down/unknown)
   - threshold_ms (timeout for pings)
 - configured_routes with same prefix and next_hop are considered identical
   
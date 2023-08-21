"""
A routing protocol needs to have a RIB (Routing Information Base).
A routing protocol needs to have some way of CRUDing the RIB.
A routing protocol needs to have some way of exchanging routes with other protocols (redistribution).
A routing protocol needs to have some way of exchanging routes with other routers (adjacency). (this example WON'T have that)

this will be a simple protocol that will have a RIB and will be able to CRUD it.  It will also be able to
send/receive routes with other protocols (redistribution).  It will NOT be able to send/receive routes with other routers (adjacency).
It will be able to update the RIB based on next hop availability (pinging the next hop).

redistribution depends on the source of the route.  Instead of stateful redistribution, a redistribution source will
supply all of its routes to the routing protocol.  The routing protocol will replace any old set of routes from this source
with the new set.  The protocol is free to optimize this, but it must be able to handle the case where old routes are
no longer present in the new set of routes.

routes will be handled as prefixes using the built-in ipaddress module.
"""

import time

from src.fp_interface import ForwardingPlane
from src.system import RouteStatus, SourceCode, Route, RIBRouteEntry, RIB

class PRoute(Route):
    def __init__(self, prefix: str, next_hop: str, metric: int, threshold_ms: int):
        super().__init__(prefix, next_hop)
        self.source = SourceCode.BASIC
        self.metric = metric
        self.threshold_ms = threshold_ms


class RoutingProtocolBasic:

    def __init__(self, fp: ForwardingPlane):
        self.fp = fp
        self.rib = RIB()
        self.configured_routes: set[Route] = set()

    def configure_route(self, route: Route):
        """configure_route will add the given route to the RIB."""
        rib_route_entry = RIBRouteEntry(route.prefix, route.next_hop, SourceCode.BASIC, 1, 1, RouteStatus.DOWN)
        self.rib.add_route_entry(rib_route_entry)

    def redistribute_in(self, routes: set[Route], source: SourceCode):
        """redistribute_in will replace all routes from the given source with the given routes."""
        self.rib.remove_route_entries_from_source(source)
        for route in routes:
            rib_route_entry = RIBRouteEntry(route.prefix, route.next_hop, source, 1, 1, RouteStatus.UP)
            self.rib.add_route_entry(rib_route_entry)

    @property
    def _local_routes(self) -> set[RIBRouteEntry]:
        """_localRoutes will return all RIBRouteEntries that are sourced from this protocol."""
        return self.rib.rib_entries_from_search(source=SourceCode.BASIC)



    def evaluate_route(self, rib_route_entry: RIBRouteEntry):
        """evaluate_route will evaluate the given route in the RIB."""
        if rib_route_entry.status == RouteStatus.UP or time.time() - rib_route_entry.last_updated > 60:
            rtt = self.fp.ping(rib_route_entry.next_hop)
            if rtt == -1:
                rib_route_entry.status = RouteStatus.DOWN
                rib_route_entry.last_updated = time.time()
            else:
                rib_route_entry.status = RouteStatus.UP
                rib_route_entry.last_updated = time.time()

    def evaluate_routes(self):
        """evaluate_routes will evaluate all routes in the RIB."""
        for rib_route_entry in self.rib.routes:
            self.evaluate_route(rib_route_entry)
    
"""
A routing protocol needs to have a RIB (Routing Information Base).
A routing protocol needs to have some way of CRUDing the RIB.
A routing protocol needs to have some way of exchanging routes with other protocols (redistribution). (this example WON'T have that)
A routing protocol needs to have some way of exchanging routes with other routers (adjacency). (this example WON'T have that)
A routing protocol needs to have some way of configuring routes and the protocol itself. (this example WILL have that)

this will be a simple protocol that will have a RIB and will be able to CRUD it.  It will not be able to
send/receive routes with other protocols (redistribution).  It will NOT be able to send/receive routes with other routers (adjacency).
It will be able to update the RIB based on next hop availability (pinging the next hop).

redistribution depends on the source of the route.  Instead of stateful redistribution, a redistribution source will
supply all of its routes to the routing protocol.  The routing protocol will replace any old set of routes from this source
with the new set.  The protocol is free to optimize this, but it must be able to handle the case where old routes are
no longer present in the new set of routes.

routes will be handled as prefixes using the built-in ipaddress module.

since this protocol does not have redistribution, it will only have configured routes.  Configured routes are the only routes that will be in the RIB.
"""

import time

from .rib import RIBRouteEntry
from src.fp_interface import ForwardingPlane
from system import SourceCode, RouteStatus, Route


class PBRoute(Route):
    def __init__(self, prefix: str, next_hop: str, metric: int, threshold_ms: int):
        super().__init__(prefix, next_hop)
        self.source = SourceCode.BASIC
        self.metric = metric
        self.threshold_ms = threshold_ms
        # self._value = self.prefix, self.next_hop, self.source, self.metric, self.threshold_ms
        self._value = self.prefix, self.next_hop  # including source, metric, and threshold don't seem to be a good idea

    # __hash__ and __eq__ are defined in Route!


class RoutingProtocolBasic:
    source_code = SourceCode.BASIC
    def __init__(self, fp: ForwardingPlane):
        self.fp = fp
        self.configured_routes: set[PBRoute] = set()

    def add_confiugred_route(self, route: Route, metric: int, threshold_ms: int):
        """configure_route will add the given route to the RIB."""
        pb_route = PBRoute(route.prefix, route.next_hop, metric, threshold_ms)
        self.configured_routes.add(pb_route)

    def remove_configured_route(self, route: Route):
        """remove_configured_route will remove the given route from the RIB."""
        # this seems okay, but might be a problem later because of how hashing works
        pb_route = PBRoute(route.prefix, route.next_hop, 0, 0)
        self.configured_routes.discard(pb_route)

    def evaluate_route(self, pb_route: PBRoute):
        """evaluate_route will evaluate the given route in the RIB."""
        if (
            pb_route.status == RouteStatus.UP
            or time.time() - pb_route.last_updated > 60
        ):
            rtt = self.fp.ping(pb_route.next_hop)
            if rtt == -1:
                pb_route.status = RouteStatus.DOWN
                pb_route.last_updated = time.time()
            else:
                pb_route.status = RouteStatus.UP
                pb_route.last_updated = time.time()

    def evaluate_routes(self):
        """evaluate_routes will evaluate all routes in the configured_routes."""
        for rib_route_entry in self.configured_routes:
            self.evaluate_route(rib_route_entry)



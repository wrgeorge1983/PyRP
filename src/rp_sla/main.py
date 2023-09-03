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

from src.config import Config
from src.fp_interface import ForwardingPlane
from src.system import SourceCode, RouteStatus, IPNetwork
from src.generic.rib import Route


class SLA_Route(Route):
    def __init__(self, prefix: str, next_hop: str, priority: int, threshold_ms: int):
        super().__init__(prefix, next_hop)
        self.source = SourceCode.SLA
        self.priority = priority
        self.threshold_ms = threshold_ms
        self.status = RouteStatus.UNKNOWN
        self.last_updated = time.time()
        # self._value = self.prefix, self.next_hop, self.source, self.metric, self.threshold_ms
        self._value = (
            self.prefix,
            self.next_hop,
        )  # including source, metric, and threshold don't seem to be a good idea

    @property
    def as_json(self):
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "source": self.source.value,
            "priority": self.priority,
            "threshold_ms": self.threshold_ms,
            "status": self.status.value,
            "last_updated": self.last_updated,
        }
    # __hash__ and __eq__ are defined in Route!


class RP_SLA:
    source_code = SourceCode.SLA

    def __init__(
        self,
        fp: ForwardingPlane,
        threshold_measure_interval: int = 60,
        admin_distance: int = 1,
    ):
        self.fp = fp
        self._configured_routes: set[SLA_Route] = set()
        self._threshold_measure_interval = threshold_measure_interval
        self.admin_distance = admin_distance

    @classmethod
    def from_config(cls, config: Config, fp: ForwardingPlane):
        rslt = cls(
            fp,
            config.rp_sla.get("threshold_measure_interval", 60),
            config.rp_sla.get("admin_distance", 1),
        )
        for route in config.rp_sla.get("routes", []):
            rslt.add_configured_route(
                Route(route["prefix"], route["next_hop"]),
                route["priority"],
                route["threshold_ms"],
            )
        return rslt

    @property
    def as_json(self) -> dict[str, str | int | list[dict[str, str | int]]]:
        return {
            "admin_distance": self.admin_distance,
            "threshold_measure_interval": self._threshold_measure_interval,
            "configured_routes": [route.as_json for route in self._configured_routes],
        }

    @property
    def configured_routes(self):
        return self._configured_routes

    @property
    def up_routes(self):
        return [
            route for route in self._configured_routes if route.status == RouteStatus.UP
        ]

    def add_configured_route(self, route: Route, priority: int, threshold_ms: int):
        """configure_route will add the given route to the RIB."""
        pb_route = SLA_Route(route.prefix, route.next_hop, priority, threshold_ms)
        self._configured_routes.add(pb_route)

    def remove_configured_route(self, route: Route):
        """remove_configured_route will remove the given route from the RIB."""
        # this seems okay, but might be a problem later because of how hashing works
        pb_route = SLA_Route(route.prefix, route.next_hop, 0, 0)
        self._configured_routes.discard(pb_route)

    def evaluate_route(self, pb_route: SLA_Route):
        """evaluate_route will evaluate the given route in the RIB."""
        if (
            pb_route.status == RouteStatus.UNKNOWN
            or (time.time() - pb_route.last_updated) > self._threshold_measure_interval
        ):
            try:
                rtt = self.fp.ping(
                    pb_route.next_hop, timeout_seconds=int(pb_route.threshold_ms / 1000)
                )
                if rtt <= pb_route.threshold_ms:
                    pb_route.status = RouteStatus.UP
                else:
                    pb_route.status = RouteStatus.DOWN
            except TimeoutError:
                pb_route.status = RouteStatus.DOWN

            pb_route.last_updated = time.time()

    def evaluate_routes(self):
        """evaluate_routes will evaluate all routes in the configured_routes."""
        for pb_route in self._configured_routes:
            self.evaluate_route(pb_route)

    def export_routes(self) -> set[SLA_Route]:
        """export_routes will return a set of only best routes (up, highest priority)."""
        up_routes = self.up_routes

        best_routes: dict[IPNetwork, SLA_Route] = dict()
        for route in up_routes:
            if route.prefix not in best_routes:
                best_routes[route.prefix] = route
            else:
                if route.priority > best_routes[route.prefix].priority:
                    best_routes[route.prefix] = route

        return set(best_routes.values())
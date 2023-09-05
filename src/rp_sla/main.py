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
import abc
import time
from typing import Type, Optional

from src.config import Config
from src.fp_interface import ForwardingPlane
from src.system import RouteStatus, IPNetwork, IPAddress
from src.generic.rib import Route, RouteSpec


class SLA_RouteSpec(RouteSpec):
    priority: int
    threshold_ms: int
    last_updated: Optional[str]
    status: Optional[RouteStatus]


class SLA_Route(Route):
    intrinsic_fields = [
        "prefix",
        "next_hop",
    ]

    supplemental_fields = [
        "priority",
        "threshold_ms",
    ]

    optional_fields = ["last_updated", "status"]

    def __init__(
        self, prefix: IPNetwork, next_hop: IPAddress, priority: int, threshold_ms: int
    ):
        super().__init__(prefix, next_hop)
        self.priority = priority
        self.threshold_ms = threshold_ms
        self.status = RouteStatus.UNKNOWN
        self.last_updated = time.time()
        self._value = (
            self.prefix,
            self.next_hop,
        )  # including source, metric, and threshold don't seem to be a good idea

    @property
    def as_json(self):
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "priority": self.priority,
            "threshold_ms": self.threshold_ms,
            "status": self.status.value,
            "last_updated": self.last_updated,
        }

    # __hash__ and __eq__ are defined in Route!


class RIB_Base(metaclass=abc.ABCMeta):

    def __init__(self):
        self._table = set()

    @property
    @abc.abstractmethod
    def route_type(self) -> Type[Route]:
        pass

    @abc.abstractmethod
    def add(self, route: RouteSpec | Type[Route]):
        pass

    @abc.abstractmethod
    def remove(self, route: RouteSpec | Type[Route]):
        pass

    @abc.abstractmethod
    def discard(self, route: RouteSpec | Type[Route]):
        pass


    def _check_for_intrinsic_values(self, **kwargs) -> None:
        missing_fields = []
        for key in self.route_type.intrinsic_fields:
            if key not in kwargs:
                missing_fields.append(key)

        if missing_fields:
            raise ValueError(f"Missing Fields: {missing_fields}")

    def _check_for_invalid_fields(self, **kwargs) -> None:
        """Raises ValueError with any invalid fields that are found"""
        valid_fields = (
            self.route_type.intrinsic_fields
            + self.route_type.supplemental_fields
            + self.route_type.optional_fields
        )
        invalid_fields = []
        for key in kwargs:
            if key not in valid_fields:
                invalid_fields.append(key)

        if invalid_fields:
            raise ValueError(f"Invalid fields: {invalid_fields}")

    def _validate_fields(self, **kwargs):
        self._check_for_intrinsic_values(**kwargs)
        self._check_for_invalid_fields(**kwargs)

    def export_routes(self) -> list[RouteSpec]:
        result = [
            route.as_json
            for route in self._table
        ]
        return result

    def import_routes(self, routes: list[RouteSpec]):
        self._table = {
            self.route_type(**route)
            for route in routes
        }


class SLA_RIB(RIB_Base):
    route_type: Type[Route] = SLA_Route

    def __init__(self):
        self._table: set[SLA_Route] = set()

    @property
    def items(self):
        return set(x for x in self._table)

    def add(self, route: SLA_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.add(route)

    def remove(self, route: SLA_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.discard(route)

    discard = remove


class RP_SLA:
    route_type: Type[Route] = SLA_Route

    def __init__(
        self,
        fp: ForwardingPlane,
        threshold_measure_interval: int = 60,
        admin_distance: int = 1,
    ):
        self.fp = fp
        self._configured_routes = SLA_RIB()
        self._rib = SLA_RIB()
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
            route: SLA_RouteSpec
            rslt.add_configured_route(route)
        return rslt

    @property
    def as_json(self) -> dict[str, str | int | list[dict[str, str | int]]]:
        return {
            "admin_distance": self.admin_distance,
            "threshold_measure_interval": self._threshold_measure_interval,
            "configured_routes": [
                route.as_json for route in self._configured_routes.items
            ],
        }

    @property
    def configured_routes(self):
        return self._configured_routes.items

    @property
    def rib_routes(self):
        return self._rib.items

    @property
    def up_routes(self):
        return [
            route for route in self.rib_routes if route.status == RouteStatus.UP
        ]

    def add_configured_route(self, route: SLA_RouteSpec | route_type):
        self._configured_routes.add(route)
        self._rib.add(route)

    def remove_configured_route(self, route: SLA_RouteSpec | route_type):
        self._configured_routes.discard(route)
        self._rib.discard(route)

    def reset_rib(self):
        configured_routes = self._configured_routes.export_routes()
        self._rib = SLA_RIB()
        self._rib.import_routes(configured_routes)

    def evaluate_route(self, sla_route: SLA_Route):
        """evaluate_route will evaluate the given route in the RIB."""
        if (
            sla_route.status == RouteStatus.UNKNOWN
            or (time.time() - sla_route.last_updated) > self._threshold_measure_interval
        ):
            try:
                rtt = self.fp.ping(
                    sla_route.next_hop,
                    timeout_seconds=int(sla_route.threshold_ms / 1000),
                )
                if rtt <= sla_route.threshold_ms:
                    sla_route.status = RouteStatus.UP
                else:
                    sla_route.status = RouteStatus.DOWN
            except TimeoutError:
                sla_route.status = RouteStatus.DOWN

            sla_route.last_updated = time.time()

    def evaluate_routes(self):
        """evaluate_routes will evaluate all routes in the configured_routes."""
        for sla_route in self._rib.items:
            self.evaluate_route(sla_route)

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

"""
implements the original RIPv1 protocol as specified in RFC 1058 (https://datatracker.ietf.org/doc/html/rfc1058)


"""
import time
from typing import Literal, Optional, Type
from typing_extensions import TypedDict

from src.config import Config
from src.generic.rib import RouteSpec, Route, RIB_Base
from src.system import SourceCode, RouteStatus, IPNetwork, IPAddress


class RIP1_RouteSpec(RouteSpec):
    metric: int
    route_source: Literal[SourceCode.RIP1]
    last_updated: Optional[float]
    status: Optional[RouteStatus]

class RIP1_Route(Route):
    intrinsic_fields = ["prefix", "next_hop"]
    supplemental_fields = ["metric"]
    optional_fields = ["last_updated", "status", "route_source"]

    def __init__(self, prefix: IPNetwork, next_hop: IPAddress, metric: int, *args, strict: bool = True, **kwargs):
        if strict:
            if kwargs:
                raise ValueError(f"unexpected fields: {kwargs.keys()}")
            if args:
                raise ValueError(f"unexpected positional values: {args}")

        super().__init__(prefix, next_hop)
        self.metric = metric
        self.status = RouteStatus.UNKNOWN
        self.last_updated = time.time()
        self._value = (self.prefix, self.next_hop)

    @property
    def as_json(self) -> RIP1_RouteSpec:
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "metric": self.metric,
            "status": self.status.value,
            "last_updated": self.last_updated,
            "route_source": SourceCode.RIP1.value,
        }

class RIP1_RPSpec(TypedDict):
    admin_distance: int

class RIP1_RIB(RIB_Base):
    route_type: Type[Route] = RIP1_Route

    def __init__(self):
        self._table: set[RIP1_Route] = set()

    @property
    def items(self) -> set[RIP1_Route]:
        return set(x for x in self._table)

    def add(self, route: RIP1_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.add(route)

    def remove(self, route: RIP1_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.discard(route)

    discard = remove


class RP_RIP1:
    def __init__(self, admin_distance: int = 120):
        self._rib = RIP1_RIB()
        self.admin_distance = admin_distance

    @classmethod
    def from_config(cls, config: Config):
        rslt = cls(admin_distance=config.rp_rip1["admin_distance"])
        return rslt

    @property
    def as_json(self) -> RIP1_RPSpec:
        return {
            "admin_distance": self.admin_distance,
        }

    @property
    def rib_routes(self):
        return self._rib.items

    def export_routes(self) -> set[RIP1_Route]:

        routes = self._rib.items
        best_routes: dict[IPNetwork, RIP1_Route] = dict()
        for route in routes:
            if route.prefix not in best_routes:
                best_routes[route.prefix] = route
            elif route.metric < best_routes[route.prefix].metric:
                best_routes[route.prefix] = route
        return set(best_routes.values())

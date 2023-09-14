import time
from typing import Optional, Literal, Type

from src.generic.rib import RouteSpec, Route, RIB_Base
from src.system import SourceCode, IPNetwork, IPAddress


class CP_StaticRouteSpec(RouteSpec):
    admin_distance: int
    last_updated: Optional[float]
    route_source: Literal[SourceCode.STATIC]


class CP_StaticRoute(Route):
    intrinsic_fields = [
        "prefix",
        "next_hop",
    ]

    supplemental_fields = ["admin_distance", "route_source"]

    optional_fields = ["last_updated"]

    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        admin_distance: int,
        route_source: Optional[Literal[SourceCode.STATIC]] = SourceCode.STATIC,
        *args,
        strict: bool = True,
        **kwargs,
    ):
        if strict and kwargs:
            raise ValueError(f"unexpected fields: {kwargs.keys()}")
        if strict and args:
            raise ValueError(f"unexpected positional values: {args}")

        super().__init__(prefix, next_hop)
        self.admin_distance = admin_distance
        self.last_updated = time.time()
        if route_source is None:
            self.route_source = SourceCode.STATIC
        self.route_source: Literal[SourceCode.STATIC] = route_source
        self._value = (
            self.prefix,
            self.next_hop,
        )

    @property
    def as_json(self) -> CP_StaticRouteSpec:
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "admin_distance": self.admin_distance,
            "last_updated": self.last_updated,
            "route_source": self.route_source.value,
        }


class CP_StaticTable(RIB_Base):
    route_type = CP_StaticRoute

    def __init__(self):
        self._table: set[CP_StaticRoute] = set()

    @property
    def items(self) -> set[CP_StaticRoute]:
        return set(x for x in self._table)

    def add(self, route: CP_StaticRoute | CP_StaticRouteSpec):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)
        self._table.add(route)

    def remove(self, route: CP_StaticRoute | CP_StaticRouteSpec):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.discard(route)

    discard = remove

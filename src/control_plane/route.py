from typing import Optional, Type

from src.generic.rib import RouteSpec, Route, RIB_Base
from src.system import SourceCode, RouteStatus, IPNetwork, IPAddress


class CP_RouteSpec(RouteSpec):
    route_source: SourceCode
    admin_distance: int
    last_updated: Optional[float]
    status: Optional[RouteStatus]


class CP_Route(Route):
    intrinsic_fields = [
        "prefix",
        "next_hop",
        "route_source",
    ]

    supplemental_fields = [
        "admin_distance",
    ]

    optional_fields = ["last_updated", "status"]

    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        route_source: SourceCode,
        admin_distance: int,
        last_updated: Optional[float] = None,
        status: RouteStatus = RouteStatus.UP,
        *args,
        strict: bool = True,
        **kwargs,
    ):
        if strict and kwargs:
            raise ValueError(f"unexpected fields: {kwargs.keys()}")
        if strict and args:
            raise ValueError(f"unexpected positional values: {args}")

        super().__init__(prefix, next_hop)
        self.route_source = SourceCode(route_source)
        self.admin_distance = admin_distance
        self.status = RouteStatus(status)
        self.last_updated = last_updated
        self._value = (
            self.prefix,
            self.next_hop,
            self.route_source,
        )

    @property
    def as_json(self) -> CP_RouteSpec:
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "route_source": self.route_source.value,
            "admin_distance": self.admin_distance,
            "status": self.status.value,
            "last_updated": self.last_updated,
        }

    # __hash__ and __eq__ are defined in Route!


class CP_RIB(RIB_Base):
    route_type = CP_Route

    def __init__(self):
        self._table: set[CP_Route] = set()

    @property
    def items(self) -> set[CP_Route]:
        return set(x for x in self._table)

    def add(self, route: CP_Route | RouteSpec):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)
        self._table.add(route)

    def remove(self, route: CP_Route | RouteSpec):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.discard(route)

    discard = remove

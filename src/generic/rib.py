import abc
import time
from typing import Type, Optional
from typing_extensions import TypedDict

from src.system import IPNetwork, IPAddress, SourceCode, RouteStatus
from src.system import IPNetwork, IPAddress


class RouteSpec(TypedDict):
    prefix: IPNetwork
    next_hop: IPAddress


class RedistributeInRouteSpec(RouteSpec):
    route_source: SourceCode


class RedistributeOutRouteSpec(RouteSpec):
    route_source: SourceCode
    admin_distance: int
    last_updated: float


class RIBRouteEntry:
    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        source: SourceCode,
        metric: int,
        admin_distance: int,
        status: RouteStatus,
    ):
        self.prefix = prefix
        self.next_hop = next_hop
        self.source = source
        self.metric = metric
        self.admin_distance = admin_distance
        self.status = RouteStatus(status)
        self.last_updated = time.time()
        self._value = (
            self.prefix,
            self.next_hop,
            self.source,
            # self.metric,
            self.admin_distance,
        )

    def __hash__(self):
        return hash(self._value)

    def __eq__(self, other):
        if not isinstance(other, RIBRouteEntry):
            return NotImplemented

        return self._value == other._value


class RIB:
    """RIB is a Routing Information Base.  It is a database of routes.
    there is a primary dictionary mapping prefixes (IPNetworks) to a set of RIBRouteEntries.
    there are additional secondary dictionaries mapping next hops (IPAddresses) and sources (SourceCodes) to a set of RIBRouteEntries.
    """

    def __init__(self):
        self._route_entries: set[RIBRouteEntry] = set()
        self.routes: dict[IPNetwork, set[RIBRouteEntry]] = {}
        self.next_hops: dict[IPAddress, set[RIBRouteEntry]] = {}
        self.sources: dict[SourceCode, set[RIBRouteEntry]] = {}

    def add_route_entry(self, rib_route_entry: RIBRouteEntry):
        self._route_entries.add(rib_route_entry)

        prefix = rib_route_entry.prefix
        if prefix not in self.routes:
            self.routes[prefix] = set()
        self.routes[prefix].add(rib_route_entry)

        if rib_route_entry.next_hop not in self.next_hops:
            self.next_hops[rib_route_entry.next_hop] = set()
        self.next_hops[rib_route_entry.next_hop].add(rib_route_entry)

        if rib_route_entry.source not in self.sources:
            self.sources[rib_route_entry.source] = set()
        self.sources[rib_route_entry.source].add(rib_route_entry)

    def remove_route_entry(self, rib_route_entry: RIBRouteEntry):
        self._route_entries.discard(rib_route_entry)
        prefix = rib_route_entry.prefix
        next_hop = rib_route_entry.next_hop
        source = rib_route_entry.source
        if prefix in self.routes:
            self.routes[prefix].discard(rib_route_entry)
            if not self.routes[prefix]:
                del self.routes[prefix]

        if next_hop in self.next_hops:
            self.next_hops[next_hop].discard(rib_route_entry)
            if not self.next_hops[next_hop]:
                del self.next_hops[next_hop]

        if source in self.sources:
            self.sources[source].discard(rib_route_entry)
            if not self.sources[source]:
                del self.sources[source]

    def remove_route_entries_from_source(self, source: SourceCode):
        if source in self.sources:
            for rib_route_entry in list(
                self.sources[source]
            ):  # list() is needed to avoid modifying the set while iterating over it
                self.remove_route_entry(rib_route_entry)

    def rib_entry_search(
        self,
        prefix: IPNetwork = None,
        next_hop: IPAddress = None,
        source: SourceCode = None,
    ) -> set[RIBRouteEntry]:
        """rib_entry_search will return a set of RIBRouteEntries that matches the given prefix, next_hop, and source (if given).
        If no arguments are given, all RIBRouteEntries will be returned"""
        rslt = set()
        for rib_route_entry in self._route_entries:
            if prefix and rib_route_entry.prefix != prefix:
                continue
            if next_hop and rib_route_entry.next_hop != next_hop:
                continue
            if source and rib_route_entry.source != source:
                continue
            rslt.add(rib_route_entry)

        if not rslt:
            rslt = self._route_entries

        return rslt

    def rib_entries_from_search(
        self,
        prefix: IPNetwork = None,
        next_hop: IPAddress = None,
        source: SourceCode = None,
    ) -> set[RIBRouteEntry]:
        """rib_entries_from_search will return a set of RIBRouteEntries that matches the given prefix, next_hop, and source (if given).
        If no arguments are given, all RIBRouteEntries will be returned"""
        rslt = set()
        for rib_route_entry in self._route_entries:
            if prefix and rib_route_entry.prefix != prefix:
                continue
            if next_hop and rib_route_entry.next_hop != next_hop:
                continue
            if source and rib_route_entry.source != source:
                continue
            rslt.add(rib_route_entry)

        if not rslt:
            rslt = self._route_entries

        return rslt

    def _rib_entry_in_routes(self, rib_route_entry: RIBRouteEntry) -> bool:
        try:
            return rib_route_entry in self.routes[rib_route_entry.prefix]
        except KeyError:
            return False

    def _rib_entry_in_next_hops(self, rib_route_entry: RIBRouteEntry) -> bool:
        try:
            return rib_route_entry in self.next_hops[rib_route_entry.next_hop]
        except KeyError:
            return False

    def _rib_entry_in_sources(self, rib_route_entry: RIBRouteEntry) -> bool:
        try:
            return rib_route_entry in self.sources[rib_route_entry.source]
        except KeyError:
            return False


class Route:
    intrinsic_fields = [
        "prefix",
        "next_hop",
    ]

    supplemental_fields = []

    optional_fields = []

    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        *args,
        strict: bool = True,
        **kwargs,
    ):
        if strict and kwargs:
            raise ValueError(f"unexpected fields: {kwargs.keys()}")
        if strict and args:
            raise ValueError(f"unexpected positional values: {args}")

        self.prefix = prefix
        self.next_hop = next_hop
        self._value = self.prefix, self.next_hop

    @property
    def intrinsic_values(self) -> tuple:
        results = (getattr(self, field) for field in self.intrinsic_fields)
        return tuple(results)

    @property
    def supplimental_values(self) -> tuple:
        results = (getattr(self, field) for field in self.supplemental_fields)
        return tuple(results)

    @property
    def as_json(self) -> RouteSpec:
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
        }

    def __hash__(self):
        return hash(self._value)

    def __eq__(self, other):
        try:
            return hash(self) == hash(other)
        except TypeError:
            return False


class RedistributeOutRoute(Route):
    intrinsic_fields = [
        "prefix",
        "next_hop",
        "route_source",
        "admin_distance",
    ]

    supplemental_fields = ["last_updated"]

    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        route_source: SourceCode | str,
        admin_distance: int,
        last_updated: Optional[float] = None,
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
        if last_updated is None:
            last_updated = time.time()
        self.last_updated = last_updated
        self._value = self.prefix, self.next_hop, self.route_source, self.admin_distance

    @property
    def as_json(self) -> RedistributeOutRouteSpec:
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "route_source": self.route_source.value,
            "admin_distance": self.admin_distance,
            "last_updated": self.last_updated,
        }


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
        result = [route.as_json for route in self._table]
        return result

    def import_routes(self, routes: list[RouteSpec]):
        self._table = self._table.union(
            {self.route_type(strict=False, **route) for route in routes}
        )

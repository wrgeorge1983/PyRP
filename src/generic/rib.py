import abc
import time
from typing import TypedDict

from src.system import IPNetwork, IPAddress, SourceCode, RouteStatus
from src.system import IPNetwork, IPAddress


class RouteSpec(TypedDict):
    prefix: IPNetwork
    next_hop: IPAddress

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
        self.status = status
        self.last_updated = time.time()
        self._value = (
            self.prefix,
            self.next_hop,
            self.source,
            self.metric,
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

    def __init__(self, prefix: IPNetwork, next_hop: IPAddress):
        self.prefix = prefix
        self.next_hop = next_hop
        self._value = self.prefix, self.next_hop

    @property
    def intrinsic_values(self) -> tuple:
        results = (
            getattr(self, field) for field in self.intrinsic_fields
        )
        return tuple(results)

    @property
    def supplimental_values(self) -> tuple:
        results = (
            getattr(self, field) for field in self.supplemental_fields
        )
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



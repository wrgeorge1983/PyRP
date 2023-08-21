import time

from system import IPNetwork, IPAddress, SourceCode, RouteStatus



class RIBRouteEntry:
    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        source: SourceCode,
        metric: int,
        status: RouteStatus,
        threshold_ms: int,
    ):
        self.prefix = prefix
        self.next_hop = next_hop
        self.source = source
        self.metric = metric
        self.status = status
        self.threshold_ms = threshold_ms
        self.last_updated = time.time()
        self._value = self.prefix, self.next_hop  # including source, metric, and threshold don't seem to be a good idea

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

    def add_route_entry(self, rib_route_entry: RIBRouteEntry):
        self._route_entries.add(rib_route_entry)

        prefix = rib_route_entry.prefix
        if prefix not in self.routes:
            self.routes[prefix] = set()
        self.routes[prefix].add(rib_route_entry)

        if rib_route_entry.next_hop not in self.next_hops:
            self.next_hops[rib_route_entry.next_hop] = set()
        self.next_hops[rib_route_entry.next_hop].add(rib_route_entry)


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

    def rib_entry_search(
        self,
        prefix: IPNetwork = None,
        next_hop: IPAddress = None,
    ) -> set[RIBRouteEntry]:
        """rib_entry_search will return a set of RIBRouteEntries that matches the given prefix, next_hop, and source (if given).
        If no arguments are given, all RIBRouteEntries will be returned"""
        rslt = set()
        for rib_route_entry in self._route_entries:
            if prefix and rib_route_entry.prefix != prefix:
                continue
            if next_hop and rib_route_entry.next_hop != next_hop:
                continue
            rslt.add(rib_route_entry)

        if not rslt:
            rslt = self._route_entries

        return rslt

    def rib_entries_from_search(
        self,
        prefix: IPNetwork = None,
        next_hop: IPAddress = None,
    ) -> set[RIBRouteEntry]:
        """rib_entries_from_search will return a set of RIBRouteEntries that matches the given prefix, next_hop, and source (if given).
        If no arguments are given, all RIBRouteEntries will be returned"""
        rslt = set()
        for rib_route_entry in self._route_entries:
            if prefix and rib_route_entry.prefix != prefix:
                continue
            if next_hop and rib_route_entry.next_hop != next_hop:
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

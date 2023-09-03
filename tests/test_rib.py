from ipaddress import ip_network, ip_address

import pytest
from src.system import RouteStatus, SourceCode
from generic.rib import RIBRouteEntry, RIB, Route


@pytest.fixture
def default_route():
    return Route(ip_network("0.0.0.0/0"), ip_address("1.1.1.1"))


def test_rib(default_route: Route):
    rib = RIB()
    rib_route_entry = RIBRouteEntry(
        default_route.prefix,
        default_route.next_hop,
        SourceCode.SLA,
        1,
        1,
        RouteStatus.UNKNOWN,
    )
    rib.add_route_entry(rib_route_entry)
    assert rib_route_entry in rib.routes[default_route.prefix]
    assert rib_route_entry in rib.next_hops[default_route.next_hop]
    assert rib_route_entry in rib.sources[SourceCode.SLA]

    next_hop = default_route.next_hop + 1
    rib_route_entry2 = RIBRouteEntry(
        default_route.prefix, next_hop, SourceCode.SLA, 1, 1, RouteStatus.UNKNOWN
    )
    rib.add_route_entry(rib_route_entry2)
    assert rib_route_entry2 in rib.routes[default_route.prefix]
    assert rib_route_entry2 in rib.next_hops[next_hop]
    assert rib_route_entry2 in rib.sources[SourceCode.SLA]

    rib.remove_route_entry(rib_route_entry)
    assert not rib._rib_entry_in_routes(rib_route_entry)
    assert not rib._rib_entry_in_next_hops(rib_route_entry)
    assert not rib._rib_entry_in_sources(rib_route_entry)

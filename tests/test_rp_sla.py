from ipaddress import ip_network, ip_address

import pytest

from src.rp_sla import RP_SLA
from generic.rib import Route


@pytest.fixture
def mock_fp(mocker):
    mock_fp = mocker.Mock(name="fp")
    return mock_fp


@pytest.fixture
def mock_rpb(mock_fp):
    rpb = RP_SLA(mock_fp, 0)
    return rpb


def test_rp_sla_evaluate(mock_rpb, mock_fp):
    prefix_a = ip_network("0.0.0.0/0")
    next_hop_a = ip_address("1.1.1.1")
    route_a = Route(prefix_a, next_hop_a)
    prefix_b = ip_network("0.0.0.0/0")
    next_hop_b = ip_address("1.1.1.2")
    route_b = Route(prefix_b, next_hop_b)
    mock_rpb.add_configured_route(route_a, 1, 100)
    mock_rpb.add_configured_route(route_b, 2, 50)
    mock_fp.ping.return_value = 75
    mock_rpb.evaluate_routes()
    configured_routes = mock_rpb.configured_routes
    assert len(configured_routes) == 2
    assert len(mock_rpb.up_routes) == 1
    assert mock_rpb.up_routes[0].next_hop == next_hop_a


def test_rp_sla_export(mock_rpb, mock_fp):
    prefix_a = ip_network("0.0.0.0/0")
    next_hop_a = ip_address("1.1.1.1")
    route_a = Route(prefix_a, next_hop_a)

    prefix_b = ip_network("0.0.0.0/0")
    next_hop_b = ip_address("1.1.1.2")
    route_b = Route(prefix_b, next_hop_b)

    prefix_c = ip_network("1.0.0.0/8")
    next_hop_c = ip_address("1.1.1.1")
    route_c = Route(prefix_c, next_hop_c)

    prefix_d = ip_network("1.0.0.0/8")
    next_hop_d = ip_address("1.1.1.2")
    route_d = Route(prefix_d, next_hop_d)

    mock_rpb.add_configured_route(route_a, 1, 100)
    mock_rpb.add_configured_route(route_b, 2, 50)

    mock_rpb.add_configured_route(route_c, 1, 100)
    mock_rpb.add_configured_route(route_d, 2, 100)
    mock_fp.ping.return_value = 75
    mock_rpb.evaluate_routes()
    assert len(mock_rpb.configured_routes) == 4
    assert len(mock_rpb.up_routes) == 3

    exported_routes = mock_rpb.export_routes()
    assert len(exported_routes) == 2
    assert exported_routes == {route_a, route_d}
    # this works even though the objects are of different types because of the hashing and equality functions
    # it might not be good to rely on this, but it works for now

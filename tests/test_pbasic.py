from ipaddress import ip_network, ip_address

import pytest

from src.pbasic import RoutingProtocolBasic
from system import Route


@pytest.fixture
def mock_fp(mocker):
    mock_fp = mocker.Mock(name="fp")
    return mock_fp

def test_pbasic_evaluate(mock_fp):
    rpb = RoutingProtocolBasic(mock_fp, 0)
    prefix_a = ip_network("0.0.0.0/0")
    next_hop_a = ip_address("1.1.1.1")
    route_a = Route(prefix_a, next_hop_a)
    prefix_b = ip_network("0.0.0.0/0")
    next_hop_b = ip_address("1.1.1.2")
    route_b = Route(prefix_b, next_hop_b)
    rpb.add_confiugred_route(route_a, 1, 100)
    rpb.add_confiugred_route(route_b, 2, 50)
    mock_fp.ping.return_value = 75
    configured_routes = rpb.configured_routes
    rpb.evaluate_routes()
    assert len(configured_routes) == 2
    assert len(rpb.up_routes) == 1
    assert rpb.up_routes[0].next_hop == next_hop_a


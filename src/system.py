import ipaddress
from enum import Enum


class RouteStatus(Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"
    # SUPPRESSED = "suppressed"
    # WITHDRAWN = "withdrawn"
    # etc..


class SourceCode(Enum):
    STATIC = 0
    RIP = 1
    OSPF = 2
    BGP = 3
    BASIC = 4


IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class Route:
    def __init__(self, prefix: IPNetwork, next_hop: IPAddress):
        self.prefix = prefix
        self.next_hop = next_hop
        self._value = self.prefix, self.next_hop

    def __hash__(self):
        return hash(self._value)

    def __eq__(self, other):
        if not isinstance(other, Route):
            return NotImplemented

        return self._value == other._value

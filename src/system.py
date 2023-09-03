import ipaddress
import string
from enum import Enum
import random


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
    SLA = 4


IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def generate_id(length: int = 8) -> str:
    valid_characters = string.ascii_letters + string.digits
    return "".join(random.choice(valid_characters) for _ in range(length))

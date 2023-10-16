"""
implements the original RIPv1 protocol as specified in RFC 1058 (https://datatracker.ietf.org/doc/html/rfc1058)

notbably this protocol is classful, meaning that it does not support VLSM or CIDR.
The RFC stipulates that both host addresses and subnet numbers are supported, but that they are indistinguishable from each other.

We're going to ignore both of them for now, and truncate all redistibuted routes to their classful boundaries.

"""
import ipaddress
import logging
import time
from typing import Literal, Optional, Type

import dpkt
from typing_extensions import TypedDict

from src.fp_interface import ForwardingPlane
from src.config import Config
from src.generic.rib import (
    RouteSpec,
    Route,
    RIB_Base,
    RedistributeInRouteSpec,
    RedistributeOutRouteSpec,
    RedistributeOutRoute,
)
from src.system import SourceCode, RouteStatus, IPNetwork, IPAddress

log = logging.getLogger(__name__)

RIP_MAX_METRIC = 16


class RIP1_RouteSpec(RouteSpec):
    metric: int
    route_source: SourceCode
    last_updated: Optional[float]
    status: Optional[RouteStatus]


class RIP1_Route(Route):
    intrinsic_fields = ["prefix", "next_hop"]
    supplemental_fields = ["metric"]
    optional_fields = ["last_updated", "status", "route_source"]

    def __init__(
        self,
        prefix: IPNetwork,
        next_hop: IPAddress,
        metric: int,
        *args,
        route_source: SourceCode | str = None,
        strict: bool = True,
        **kwargs,
    ):
        if strict:
            if kwargs:
                raise ValueError(f"unexpected fields: {kwargs.keys()}")
            if args:
                raise ValueError(f"unexpected positional values: {args}")

        super().__init__(prefix, next_hop)
        if route_source is None:
            route_source = SourceCode.RIP1

        if isinstance(route_source, str):
            route_source = SourceCode(route_source)

        self.route_source = route_source
        self.metric = metric
        self.status = RouteStatus.UNKNOWN
        self.last_updated = time.time()
        self._value = (self.prefix, self.next_hop)

    @property
    def as_json(self) -> RIP1_RouteSpec:
        return {
            "prefix": str(self.prefix),
            "next_hop": str(self.next_hop),
            "metric": self.metric,
            "status": self.status.value,
            "last_updated": self.last_updated,
            "route_source": self.route_source,
        }

    @property
    def classful(self) -> "RIP1_Route":
        prefix = self.prefix
        if prefix.version != 4:
            raise ValueError("only IPv4 is supported")
        class_a = ipaddress.ip_network("0.0.0.0/1")
        class_b = ipaddress.ip_network("128.0.0.0/2")
        class_c = ipaddress.ip_network("192.0.0.0/3")
        class_d = ipaddress.ip_network("224.0.0.0/4")
        net_addr = prefix.network_address
        if net_addr in class_a:
            try:
                classful_prefix = prefix.supernet(new_prefix=8)
            except ValueError:
                classful_prefix = ipaddress.ip_network(f"{net_addr}/8")

        elif net_addr in class_b:
            try:
                classful_prefix = prefix.supernet(new_prefix=16)
            except ValueError:
                classful_prefix = ipaddress.ip_network(f"{net_addr}/16")
        elif net_addr in class_c:
            try:
                classful_prefix = prefix.supernet(new_prefix=24)
            except ValueError:
                classful_prefix = ipaddress.ip_network(f"{net_addr}/24")
        else:
            raise ValueError(f"invalid prefix: {prefix}")

        return RIP1_Route(
            prefix=classful_prefix,
            next_hop=self.next_hop,
            metric=self.metric,
            route_source=self.route_source,
        )


class RIP1_RPSpec(TypedDict):
    admin_distance: int
    default_metric: int


class RIP1_FullRPSpec(RIP1_RPSpec):
    rib: list[RIP1_RouteSpec]
    redistributed_routes: list[RIP1_RouteSpec]
    learned_routes: list[RIP1_RouteSpec]


class RIP1_RIB(RIB_Base):
    route_type: Type[Route] = RIP1_Route

    def __init__(self):
        self._table: set[RIP1_Route] = set()

    @property
    def items(self) -> set[RIP1_Route]:
        return set(x for x in self._table)

    def add(self, route: RIP1_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.add(route)

    def remove(self, route: RIP1_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.discard(route)

    discard = remove


class RP_RIP1:
    dest_ip = ipaddress.ip_address("255.255.255.255")
    dest_port = 520
    src_port = 520

    def __init__(self, fp: ForwardingPlane, rp_interface: "RP_RIP1_Interface"):
        self.fp = fp
        self.rp_interface = rp_interface

    @staticmethod
    def _rte_from_route(route: RIP1_Route) -> dpkt.rip.RTE:
        rte = dpkt.rip.RTE()
        rte.family = 2
        try:
            rte.addr = int(route.prefix.network_address)
        except AttributeError:
            rte.addr = int(ipaddress.ip_network(route.prefix).network_address)
        # rte.next_hop = int(route.next_hop)
        rte.next_hop = int(
            ipaddress.ip_address("0.0.0.0")
        )  # we are always the next hop
        rte.metric = min(
            route.metric + 1, RIP_MAX_METRIC
        )  # we're assuming link cost is always 1

        return rte

    def send_response(self):
        rtes = [
            self._rte_from_route(route) for route in self.rp_interface.export_routes()
        ]

        rip = dpkt.rip.RIP()
        rip.cmd = dpkt.rip.RESPONSE
        rip.v = 1
        rip.rsvd = 0
        rip.auth = None
        rip.rtes = rtes

        self.fp.send_udp(str(self.dest_ip), bytes(rip), self.dest_port, self.src_port)


class RP_RIP1_Interface:
    def __init__(
        self,
        fp: ForwardingPlane,
        admin_distance: int = 120,
        default_metric: int = 1,
        redistribute_static_in: bool = False,
        redistribute_static_metric: int = 1,
        redistribute_sla_in: bool = False,
        redistribute_sla_metric: int = 1,
    ):
        self.fp = fp
        self._rib = RIP1_RIB()
        self._learned_routes = RIP1_RIB()
        self._redistributed_routes = RIP1_RIB()
        self.admin_distance = admin_distance
        self.default_metric = default_metric
        self.redistribute_in_sources = []
        self.redistribute_in_metrics = {
            SourceCode.STATIC: redistribute_static_metric,
            SourceCode.SLA: redistribute_sla_metric,
        }
        if redistribute_static_in:
            self.redistribute_in_sources.append(SourceCode.STATIC)
        if redistribute_sla_in:
            self.redistribute_in_sources.append(SourceCode.SLA)

        self._rp = RP_RIP1(self.fp, self)

    @classmethod
    def from_config(cls, config: Config, fp: ForwardingPlane):
        rslt = cls(
            fp,
            admin_distance=config.rp_rip1["admin_distance"],
            default_metric=config.rp_rip1["default_metric"],
            redistribute_static_in=config.rp_rip1["redistribute_static_in"],
            redistribute_static_metric=config.rp_rip1["redistribute_static_metric"],
            redistribute_sla_in=config.rp_rip1["redistribute_sla_in"],
            redistribute_sla_metric=config.rp_rip1["redistribute_sla_metric"],
        )
        return rslt

    @property
    def as_json(self) -> RIP1_RPSpec:
        return {
            "admin_distance": self.admin_distance,
            "default_metric": self.default_metric,
        }

    @property
    def full_as_json(self) -> RIP1_FullRPSpec:
        return {
            "admin_distance": self.admin_distance,
            "default_metric": self.default_metric,
            "rib": [route.as_json for route in self._rib.items],
            "redistributed_routes": [
                route.as_json for route in self._redistributed_routes.items
            ],
            "learned_routes": [route.as_json for route in self._learned_routes.items],
        }

    @property
    def rib_routes(self):
        return self._rib.items

    def export_routes(self) -> set[RIP1_Route]:
        routes = self._rib.items
        best_routes: dict[IPNetwork, RIP1_Route] = dict()
        for route in routes:
            if route.prefix not in best_routes:
                best_routes[route.prefix] = route
            elif route.metric < best_routes[route.prefix].metric:
                best_routes[route.prefix] = route
        return set(best_routes.values())

    def redistribute_out(self) -> list[RedistributeOutRoute]:
        routes = (
            route for route in self._rib.items if route.route_source == SourceCode.RIP1
        )
        best_routes: dict[IPNetwork, RIP1_Route] = dict()
        for route in routes:
            if route.prefix not in best_routes:
                best_routes[route.prefix] = route
            elif route.metric < best_routes[route.prefix].metric:
                best_routes[route.prefix] = route
        rslt = []
        for route in best_routes.values():
            json_route = route.as_json
            json_route.update({
                "admin_distance": self.admin_distance,
                "route_source": SourceCode.RIP1,
            })
            rslt.append(RedistributeOutRoute(**json_route, strict=False))
        return rslt
        # return [
        #     RedistributeOutRoute(
        #         **route.as_json,
        #         admin_distance=self.admin_distance,
        #         route_source=SourceCode.RIP1,
        #     )
        #     for route in best_routes.values()
        # ]

    def redistribute_in(
        self, route_specs: list[RedistributeInRouteSpec | RIP1_RouteSpec]
    ):
        self._redistributed_routes = RIP1_RIB()
        for route_spec in route_specs:
            if "metric" not in route_spec:
                route_spec["metric"] = self.redistribute_in_metrics.get(
                    route_spec["route_source"], self.default_metric
                )
                route_spec["metric"] = min(route_spec["metric"], RIP_MAX_METRIC)
            source = SourceCode(route_spec["route_source"])
            if source not in self.redistribute_in_sources:
                log.debug(
                    f"skipping route {route_spec} because source {source} is not in {self.redistribute_in_sources}"
                )
                continue

            route = RIP1_Route(**route_spec)
            route = route.classful
            self._redistributed_routes.add(route)

    def refresh_rib(self):
        self._rib = RIP1_RIB()
        self._rib.import_routes(self._redistributed_routes.export_routes())
        self._rib.import_routes(self._learned_routes.export_routes())

    def send_response(self):
        self._rp.send_response()

    def handle_response(self, rip: dpkt.rip.RIP, addr: tuple[str, int]):
        for rte in rip.rtes:
            try:
                route = RIP1_Route(
                    prefix=ipaddress.ip_network(ipaddress.ip_address(rte.addr)),
                    next_hop=ipaddress.ip_address(rte.next_hop),
                    metric=rte.metric,
                )
                classful_route = route.classful
                if classful_route.metric >= RIP_MAX_METRIC:
                    log.warning(f"ignoring route with metric >= {RIP_MAX_METRIC}")
                    continue
                if classful_route.next_hop == ipaddress.ip_address("0.0.0.0"):
                    log.debug(f'updating next_hop of 0.0.0.0 to {addr[0]}')
                    classful_route.next_hop = ipaddress.ip_address(addr[0])

                log.info(f'classful route: {classful_route.as_json}')
                self._learned_routes.add(classful_route)
            except ValueError:
                log.info(
                    f"received invalid route: {rte.addr=}, {rte.next_hop=}, {rte.metric=}"
                )
                continue

    def handle_udp_bytes(self, data: bytes, addr: tuple[str, int]):
        log.debug(f"handling_udp_bytes: {data=}, {addr=}")
        rip = dpkt.rip.RIP(data)
        log.debug(f"received RIP packet: {rip.auth=}, {rip.data=}")
        match rip.cmd:
            case dpkt.rip.REQUEST:
                log.debug(f"received RIP request: {rip.data=}")
            case dpkt.rip.RESPONSE:
                log.debug(f"received RIP response: {rip.data=}")
                self.handle_response(rip, addr)
            case _:
                log.info(f"received RIP packet with unexpected command: {rip.cmd}")
        return


    async def listen_udp(self, callback: callable):
        await self.fp.listen_udp(self._rp.dest_port, callback)
        return

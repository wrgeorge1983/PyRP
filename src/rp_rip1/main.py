"""
implements the original RIPv1 protocol as specified in RFC 1058 (https://datatracker.ietf.org/doc/html/rfc1058)

notbably this protocol is classful, meaning that it does not support VLSM or CIDR.
The RFC stipulates that both host addresses and subnet numbers are supported, but that they are indistinguishable from each other.

We're going to ignore both of them for now, and truncate all redistibuted routes to their classful boundaries.

"""
import asyncio
import ipaddress
import logging
import random
import time
from typing import Literal, Optional, Type

import dpkt
from typing_extensions import TypedDict

from src.control_plane.clients.client_control_plane import RpCpClient
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
RIP_ROUTE_TIMEOUT = 180
RIP_ROUTE_GARBAGE_TIMER = 120
# RIP_ROUTE_TIMEOUT = 10
# RIP_ROUTE_GARBAGE_TIMER = 60
RIP_ROUTE_GARBAGE_TIMEOUT = RIP_ROUTE_TIMEOUT + RIP_ROUTE_GARBAGE_TIMER
RIP_HOUSEKEEPING_INTERVAL = 1


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
    cp_id: Optional[str]


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

        self._table.discard(route)  # required to update routes?
        self._table.add(route)

    def remove(self, route: RIP1_RouteSpec | route_type):
        if isinstance(route, dict):
            self._validate_fields(**route)
            route = self.route_type(**route)

        self._table.discard(route)

    discard = remove


class RP_RIP1:
    default_dst_ip = ipaddress.ip_address("172.24.0.255")
    default_dst_port = 520
    default_src_port = 520

    def __init__(self, fp: ForwardingPlane, rp_interface: "RP_RIP1_Interface"):
        """This is the inner class for the protocol itself, responsible primarily for message passing to/from the FP"""
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

    def send_response(
        self, dst_ip: Optional[str] = None, dst_port: Optional[int] = None
    ) -> int:
        if dst_ip is None:
            dst_ip = str(self.default_dst_ip)

        if dst_port is None:
            dst_port = self.default_dst_port

        log.info(f"sending response msg")
        rtes = [
            self._rte_from_route(route) for route in self.rp_interface.export_routes()
        ]

        rip = dpkt.rip.RIP()
        rip.cmd = dpkt.rip.RESPONSE
        rip.v = 1
        rip.rsvd = 0
        rip.auth = None
        rip.rtes = rtes

        return self.fp.send_udp(bytes(rip), dst_ip, dst_port, self.default_src_port)

    def send_request(self) -> int:
        log.info(f"sending request message")
        rip = dpkt.rip.RIP()
        rip.cmd = dpkt.rip.REQUEST
        rip.v = 1
        rip.rsvd = 0
        rip.auth = None

        request_rte = dpkt.rip.RTE()
        request_rte.family = 0
        request_rte.addr = 0
        request_rte.metric = RIP_MAX_METRIC

        rip.rtes = [request_rte]

        return self.fp.send_udp(
            bytes(rip),
            str(self.default_dst_ip),
            self.default_dst_port,
            # self.default_src_port,
        )

    @staticmethod
    def handle_response(
        rip_pkt: dpkt.rip.RIP, src_tuple: tuple[str, int]
    ) -> list[RIP1_Route]:
        """In RIPv1 a 'Response' is always and exclusively the message that contains route entries"""
        src_ip, src_port = src_tuple
        routes: list[RIP1_Route] = []
        for rte in rip_pkt.rtes:
            try:
                route = RIP1_Route(
                    prefix=ipaddress.ip_network(ipaddress.ip_address(rte.addr)),
                    next_hop=ipaddress.ip_address(rte.next_hop),
                    metric=rte.metric,
                )
                classful_route = route.classful
                if classful_route.metric >= RIP_MAX_METRIC:
                    log.warning(f"poisoning route with metric >= {RIP_MAX_METRIC}")
                    classful_route.metric = RIP_MAX_METRIC
                    classful_route.status = RouteStatus.DOWN
                else:
                    classful_route.status = RouteStatus.UP

                if classful_route.next_hop == ipaddress.ip_address("0.0.0.0"):
                    log.debug(f"updating next_hop of 0.0.0.0 to {src_ip}")
                    classful_route.next_hop = ipaddress.ip_address(src_ip)

                log.info(f"classful route: {classful_route.as_json}")
                routes.append(classful_route)
            except ValueError:
                log.info(
                    f"received invalid route: {rte.addr=}, {rte.next_hop=}, {rte.metric=}"
                )
                continue
        return routes

    def handle_udp_bytes(self, data: bytes, src_tuple: tuple[str, int]):
        src_ip, src_port = src_tuple
        log.debug(f"handling_udp_bytes: {data=}, {src_tuple=}")
        rip_pkt = dpkt.rip.RIP(data)
        log.debug(f"received RIP packet: {rip_pkt.auth=}, {rip_pkt.data=}")
        if src_ip == self.fp.get_local_ip():
            if self.rp_interface.reject_own_messages:
                log.debug(f"ignoring own message!")
                return

            log.debug(f"processing message from self!!!")

        match rip_pkt.cmd:
            case dpkt.rip.REQUEST:  # this type of message is requesting route advertisements
                log.debug(f"received RIP request: {rip_pkt.data=}")
                self.send_response(dst_ip=src_ip, dst_port=src_port)

            case dpkt.rip.RESPONSE:  # this type of message is always for route advertisements (even event triggered ones)
                log.debug(f"received RIP response: {rip_pkt.data=}")
                routes = self.handle_response(rip_pkt, src_tuple)
                for route in routes:
                    self.rp_interface._learned_routes.add(route)
                self.rp_interface.refresh_rib(route_change=len(routes) > 0)
                if any(route.metric == RIP_MAX_METRIC for route in routes):
                    log.warning(
                        f"received poisoned route(s): {[route.as_json for route in routes]}"
                    )
                    self.send_response(
                        dst_ip=str(self.default_dst_ip), dst_port=self.default_dst_port
                    )
            case _:
                log.warning(
                    f"received RIP packet with unexpected command: {rip_pkt.cmd}"
                )

        return

    async def listen(self, src_port: Optional[int] = None):
        if src_port is None:
            src_port = self.default_src_port
        await self.fp.listen_udp(src_port, self.handle_udp_bytes)

    async def listen_timed(
        self, src_port: Optional[int] = None, timeout_seconds: int = 0
    ):
        if timeout_seconds == 0:
            await self.listen(src_port)  # no timeout
        else:
            await self.fp.listen_udp_timed(
                src_port, self.handle_udp_bytes, timeout_seconds
            )


class RP_RIP1_Interface:
    """This is the outer interface for the routing protocol"""

    def __init__(
        self,
        fp: ForwardingPlane,
        admin_distance: int = 120,
        default_metric: int = 1,
        redistribute_static_in: bool = False,
        redistribute_static_metric: int = 1,
        redistribute_sla_in: bool = False,
        redistribute_sla_metric: int = 1,
        advertisement_interval: int = 5,
        request_interval: int = 30,
        reject_own_messages: bool = False,
        cp_id: str = None,
        trigger_redistribution: bool = False,
        cp_client: RpCpClient = None,
    ):
        self.fp = fp
        self._rib = RIP1_RIB()
        self._learned_routes = RIP1_RIB()
        self._redistributed_routes = RIP1_RIB()
        self.admin_distance = admin_distance
        self.default_metric = default_metric
        self.advertisement_interval = advertisement_interval
        self.request_interval = request_interval
        self.redistribute_in_sources = []
        self.redistribute_in_metrics = {
            SourceCode.STATIC: redistribute_static_metric,
            SourceCode.SLA: redistribute_sla_metric,
        }
        if redistribute_static_in:
            self.redistribute_in_sources.append(SourceCode.STATIC)
        if redistribute_sla_in:
            self.redistribute_in_sources.append(SourceCode.SLA)

        self.small_rand_sleeps = True
        self.reject_own_messages = reject_own_messages
        self.trigger_redistribution = trigger_redistribution
        self._rp = RP_RIP1(self.fp, self)
        self.cp_id = cp_id
        self._cp = cp_client

    @staticmethod
    def small_sleep():
        duration_ms = random.randint(0, 300) / 1000
        log.info(f"sleeping for {duration_ms} ms")
        time.sleep(duration_ms)

    @classmethod
    def from_config(cls, config: Config, fp: ForwardingPlane, cp_id: str):
        rslt = cls(
            fp,
            admin_distance=config.rp_rip1["admin_distance"],
            default_metric=config.rp_rip1["default_metric"],
            redistribute_static_in=config.rp_rip1["redistribute_static_in"],
            redistribute_static_metric=config.rp_rip1["redistribute_static_metric"],
            redistribute_sla_in=config.rp_rip1["redistribute_sla_in"],
            redistribute_sla_metric=config.rp_rip1["redistribute_sla_metric"],
            advertisement_interval=config.rp_rip1["advertisement_interval"],
            request_interval=config.rp_rip1["request_interval"],
            reject_own_messages=config.rp_rip1["reject_own_messages"],
            cp_client=RpCpClient(config.rp_rip1["cp_base_url"]),
            cp_id=cp_id,
            trigger_redistribution=config.rp_rip1["trigger_redistribution"],
        )
        return rslt

    @property
    def as_json(self) -> RIP1_RPSpec:
        return {
            "admin_distance": self.admin_distance,
            "default_metric": self.default_metric,
            "cp_id": self.cp_id,
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
            "cp_id": self.cp_id,
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
            route
            for route in self._rib.items
            if route.route_source == SourceCode.RIP1 and route.metric < RIP_MAX_METRIC
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
            json_route.update(
                {
                    "admin_distance": self.admin_distance,
                    "route_source": SourceCode.RIP1,
                }
            )
            rslt.append(RedistributeOutRoute(**json_route, strict=False))
        return rslt

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

    def refresh_rib(self, route_change: bool = False):
        self._rib = RIP1_RIB()
        self._rib.import_routes(self._redistributed_routes.export_routes())
        self._rib.import_routes(self._learned_routes.export_routes())

        if route_change and self.trigger_redistribution:
            asyncio.create_task(self._cp.redistribute(self.cp_id))

    async def send_response(self):
        self._rp.send_response()

    async def send_request(self) -> int:
        return self._rp.send_request()

    async def listen(self):
        await self._rp.listen()

    async def run_advertisements(self):
        log.info(f"in async def run_advertisements")
        while True:
            await self.send_response()
            await asyncio.sleep(self.advertisement_interval)

    async def run_requests(self):
        log.info(f"in async def run_requests")
        while True:
            port = await self.send_request()
            log.info(f"request sent on port {port}")
            log.info(f"listening on port {port}")
            await self._rp.listen_timed(port, self.request_interval - 1)
            await asyncio.sleep(1)  # finish out the request_interval

    async def check_routes(self):
        log.info(f"in async def check_routes")
        route_change = False
        while True:
            # check learned routes for expiration
            for route in self._learned_routes.items:
                if route.last_updated + RIP_ROUTE_GARBAGE_TIMEOUT < time.time():
                    log.info(f"removing route {route.as_json}")
                    self._learned_routes.remove(route)
                    route_change = True
                elif route.last_updated + RIP_ROUTE_TIMEOUT < time.time():
                    if route.metric >= RIP_MAX_METRIC:
                        continue  # don't bother with routes that are already maxed out

                    log.info(f"marking route {route.as_json} as down")
                    route.status = RouteStatus.DOWN
                    route.metric = RIP_MAX_METRIC
                    route_change = True

            self.refresh_rib(route_change)

            if route_change and self.trigger_redistribution:
                # await self._cp.redistribute(self.cp_id)
                route_change = False
                asyncio.create_task(self._cp.redistribute(self.cp_id))

            await asyncio.sleep(RIP_HOUSEKEEPING_INTERVAL)

    def run_protocol(self):
        log.info("about to listen")

        asyncio.create_task(self.listen())
        if self.request_interval > 0:
            asyncio.create_task(self.run_requests())
        if self.advertisement_interval > 0:
            asyncio.create_task(self.run_advertisements())
        if RIP_HOUSEKEEPING_INTERVAL > 0:
            asyncio.create_task(self.check_routes())

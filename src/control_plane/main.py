from typing import Optional
from typing_extensions import TypedDict

from src.config import Config
from src.generic.rib import RouteSpec
from src.system import SourceCode, RouteStatus, IPNetwork
from .clients import RpSlaClient, RpRip1Client
from .route import CP_RIB, CP_Route
from .static import CP_StaticTable, CP_StaticRouteSpec


class CP_Spec(TypedDict):
    hostname: str
    rp_sla_enabled: bool
    rp_sla_instance: Optional[str]
    rp_rip1_enabled: bool
    rp_rip1_instance: Optional[str]
    static_routes: list[RouteSpec]


class ControlPlane:
    def __init__(self, hostname: str, rp_sla_client: Optional[RpSlaClient], rp_rip1_client: Optional[RpRip1Client]):
        self.hostname = hostname
        self.rp_sla_client = rp_sla_client
        self.rp_sla_enabled = rp_sla_client is not None
        self.rp_sla_instance: Optional[str] = None

        self.rp_rip1_client = rp_rip1_client
        self.rp_rip1_enabled = rp_rip1_client is not None
        self.rp_rip1_instance: Optional[str] = None

        self._static_routes = CP_StaticTable()
        self._rib = CP_RIB()
        self.config: Optional[Config] = None

    def initialize_rp_sla(self):
        if self.rp_sla_enabled:
            result = self.rp_sla_client.create_instance_from_config(
                filename=self.config.filename
            )
            self.rp_sla_instance = result["instance_id"]

    def initialize_rp_rip1(self):
        if self.rp_rip1_enabled:
            result = self.rp_rip1_client.create_instance_from_config(
                filename=self.config.filename
            )
            self.rp_rip1_instance = result["instance_id"]


    @classmethod
    def from_config(cls, config: Config):
        if config.rp_sla["enabled"]:
            rp_sla_client = RpSlaClient(config.control_plane["rp_sla_base_url"])
        else:
            rp_sla_client = None

        if config.rp_rip1["enabled"]:
            rp_rip1_client = RpRip1Client(config.control_plane["rp_rip1_base_url"])
        else:
            rp_rip1_client = None

        rslt = cls(config.control_plane["hostname"], rp_sla_client, rp_rip1_client)
        rslt.config = config
        rslt.initialize_rp_sla()
        rslt.initialize_rp_rip1()

        for route in config.control_plane["static_routes"]:
            route: CP_StaticRouteSpec
            route["route_source"] = SourceCode.STATIC
            route.setdefault("admin_distance", 1)
            rslt.add_static_route(route)

        return rslt

    @property
    def up_routes(self):
        return [route for route in self._rib.items if route.status in (RouteStatus.UP, RouteStatus.UP.value)]

    def add_static_route(self, route: CP_StaticRouteSpec, rib_sync: bool = True):
        self._static_routes.add(route)
        if rib_sync:
            self._rib.add(route)

    def remove_static_route(self, route: CP_StaticRouteSpec, rib_sync: bool = True):
        self._static_routes.discard(route)
        if rib_sync:
            self._rib.discard(route)

    def refresh_rib(self) -> list[RouteSpec]:
        static_routes = self._static_routes.export_routes()
        self._rib = CP_RIB()

        self._rib.import_routes(static_routes)
        if self.rp_sla_enabled:
            # sla_routes = self.rp_sla_client.get_rib_routes(self.rp_sla_instance)
            sla_routes = self.rp_sla_client.get_best_routes(self.rp_sla_instance)
            sla_routes = [
                route for route in sla_routes if route["status"] in (RouteStatus.UP, RouteStatus.UP.value)
            ]
            for route in sla_routes:
                route["route_source"] = SourceCode.SLA
                route.setdefault("admin_distance", self.config.rp_sla["admin_distance"])

            self._rib.import_routes(sla_routes)

        return [route.as_json for route in self._rib.items]

    def export_routes(self) -> set[CP_Route]:
        up_routes = self.up_routes
        best_routes: dict[IPNetwork, CP_Route] = dict()
        for route in up_routes:
            if route.prefix not in best_routes:
                best_routes[route.prefix] = route
            elif route.admin_distance < best_routes[route.prefix].admin_distance:
                best_routes[route.prefix] = route
        return set(best_routes.values())

    def rp_sla_evaluate_routes(self):
        if self.rp_sla_enabled:
            return self.rp_sla_client.evaluate_routes(self.rp_sla_instance)
        return {"error": "RP_SLA not enabled"}

    @property
    def as_json(self) -> CP_Spec:
        return {
            "hostname": self.hostname,
            "rp_sla_enabled": self.rp_sla_enabled,
            "rp_sla_instance": self.rp_sla_instance,
            "rp_rip1_enabled": self.rp_rip1_enabled,
            "rp_rip1_instance": self.rp_rip1_instance,
            "static_routes": [route.as_json for route in self._static_routes.items],
        }

    @property
    def rib_routes(self):
        return self._rib.items

    @property
    def static_routes(self):
        return self._static_routes.items

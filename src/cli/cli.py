from dataclasses import dataclass
from itertools import cycle

from aiohttp import ClientResponseError
from requests import HTTPError

from src.control_plane.clients import RpSlaClient, RpRip1Client
from src.control_plane.clients.client_control_plane import RpCpClient

http_errors = (ClientResponseError, HTTPError)


@dataclass
class State:
    cp_client: RpCpClient
    sla_client: RpSlaClient
    rip_client: RpRip1Client
    proto_table: str
    _proto_tables = cycle(["sla_rib", "rip_rib"])

    @classmethod
    def from_config(cls, config: dict):
        cp_client = RpCpClient(config["cp_base_url"])
        sla_client = RpSlaClient(config["sla_base_url"])
        rip_client = RpRip1Client(config["rip1_base_url"])
        rslt = cls(cp_client, sla_client, rip_client, proto_table=None)
        rslt.next_proto()
        return rslt

    def next_proto(self):
        self.proto_table = next(self._proto_tables)

    async def get_cp_rib_entries(self) -> list[list[str]]:
        route_entries = await self.cp_client.get_rib_routes("latest")

        return [
            [prefix[field] for field in cp_rib_table_fields] for prefix in route_entries
        ]

    async def get_sla_rib_entries(self) -> list[list[str]]:
        route_entries = await self.sla_client.get_rib_routes("latest")
        return [
            [prefix[field] for field in sla_rib_table_fields]
            for prefix in route_entries
        ]

    async def get_rip_rib_entries(self) -> list[list[str]]:
        route_entries = await self.rip_client.get_rib_routes("latest")
        return [
            [prefix[field] for field in rip_rib_table_fields]
            for prefix in route_entries
        ]


config = {
    "cp_base_url": "http://localhost:5010",
    "sla_base_url": "http://localhost:5023",
    "rip1_base_url": "http://localhost:5020",
}
state = State.from_config(config)
cp_rib_table_fields = [
    "prefix",
    "next_hop",
    "route_source",
    "admin_distance",
    "status",
    "last_updated",
]
rip_rib_table_fields = [
    "prefix",
    "next_hop",
    "route_source",
    "status",
    "last_updated",
]
sla_rib_table_fields = [
    "prefix",
    "next_hop",
    "status",
    "priority",
    "threshold_ms",
]

from typing import TypedDict, Optional

from src.generic.rib import RouteSpec
from .base import BaseClient


class RpRip1Client(BaseClient):
    def health_check(self):
        response = self.get("/")
        return response.status_code == 200 and response.json() == {"Service": "RP_RIP1"}

    def get_instances(self):
        response = self.get("/instances")
        response.raise_for_status()
        return response.json()

    def get_instance(self, instance_id):
        response = self.get(f"/instances/{instance_id}")
        response.raise_for_status()
        return response.json()

    class InstanceResponse(TypedDict):
        instance_id: str

    def create_instance(self) -> InstanceResponse:
        response = self.post("/instances/new")
        response.raise_for_status()
        return response.json()

    def create_instance_from_config(
        self, filename, cp_id: Optional[str] = None
    ) -> InstanceResponse:
        response = self.post(
            "/instances/new_from_config", params={"filename": filename, "cp_id": cp_id}
        )
        response.raise_for_status()
        return response.json()

    def delete_instance(self, instance_id) -> InstanceResponse:
        response = self.delete(f"/instances/{instance_id}")
        response.raise_for_status()
        return response.json()

    async def get_rib_routes(self, instance_id):
        response = await self.aget(f"/instances/{instance_id}/routes/rib")
        return response

    def get_best_routes(self, instance_id):
        response = self.get(f"/instances/{instance_id}/best_routes")
        response.raise_for_status()
        return response.json()

    def redistribute_in(self, instance_id, routes: list[RouteSpec]):
        response = self.post(f"/instances/{instance_id}/redistribute_in", json=routes)
        response.raise_for_status()
        return response.json()

    def redistribute_out(self, instance_id):
        response = self.post(f"/instances/{instance_id}/redistribute_out")
        response.raise_for_status()
        return response.json()

    def refresh_rib(self, instance_id):
        response = self.post(f"/instances/{instance_id}/routes/rib/refresh")
        response.raise_for_status()
        return response.json()

    def run_protocol(self, instance_id):
        response = self.post(f"/instances/{instance_id}/run")
        response.raise_for_status()
        return response.json()

from typing import TypedDict

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

    def create_instance_from_config(self, filename) -> InstanceResponse:
        response = self.post(
            "/instances/new_from_config", params={"filename": filename}
        )
        response.raise_for_status()
        return response.json()

    def delete_instance(self, instance_id) -> InstanceResponse:
        response = self.delete(f"/instances/{instance_id}")
        response.raise_for_status()
        return response.json()

    def get_rib_routes(self, instance_id):
        response = self.get(f"/instances/{instance_id}/routes/rib")
        response.raise_for_status()
        return response.json()

    def get_best_routes(self, instance_id):
        response = self.get(f"/instances/{instance_id}/best_routes")
        response.raise_for_status()
        return response.json()

    redistribute_routes_out = get_best_routes

    def redistribute_routes_in(self, instance_id, routes: list[RouteSpec]):
        response = self.post(
            f"/instances/{instance_id}/redistribute_routes_in", json=routes
        )
        response.raise_for_status()
        return response.json()

    def refresh_rib(self, instance_id):
        response = self.post(f"/instances/{instance_id}/routes/rib/refresh")
        response.raise_for_status()
        return response.json()

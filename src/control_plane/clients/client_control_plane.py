from typing import TypedDict

from .base import BaseClient


class InstanceResponse(TypedDict):
    instance_id: str


class RpCpClient(BaseClient):
    async def health_check(self):
        response = self.get("/")
        return response.status_code == 200 and response.json() == {
            "Service": "ControlPlane"
        }

    async def get_instances(self):
        response = await self.aget("/instances")
        return response

    async def create_instance_from_config(self, config_file: str) -> InstanceResponse:
        response = await self.apost(
            "/instances/new_from_config", params={"filename": config_file}
        )
        return response

    async def get_rib_routes(self, instance_id):
        response = await self.aget(f"/instances/{instance_id}/routes")
        return response

    async def redistribute(self, instance_id):
        response_json = await self.apost(f"/instances/{instance_id}/redistribute")
        return response_json

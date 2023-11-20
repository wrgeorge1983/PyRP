from .base import BaseClient


class RpCpClient(BaseClient):
    async def health_check(self):
        response = self.get("/")
        return response.status_code == 200 and response.json() == {
            "Service": "ControlPlane"
        }

    async def get_instances(self):
        response = self.get("/instances")
        response.raise_for_status()
        return response.json()

    async def redistribute(self, instance_id):
        response_json = await self.apost(f"/instances/{instance_id}/redistribute")
        return response_json

from .base import BaseClient


class RpCpClient(BaseClient):

    def health_check(self):
        response = self.get("/")
        return response.status_code == 200 and response.json() == {"Service": "ControlPlane"}

    def get_instances(self):
        response = self.get("/instances")
        response.raise_for_status()
        return response.json()

    def redistribute(self, instance_id):
        response = self.post(f"/instances/{instance_id}/redistribute")
        response.raise_for_status()
        return response.json()

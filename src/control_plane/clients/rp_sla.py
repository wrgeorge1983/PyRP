from typing import TypedDict

import requests

class BaseClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, url, params=None):
        return self.session.get(self.base_url + url, params=params)

    def post(self, url, params=None, data=None):
        return self.session.post(self.base_url + url, params=params, data=data)

    def put(self, url, params=None, data=None):
        return self.session.put(self.base_url + url, params=params, data=data)

    def delete(self, url, params=None):
        return self.session.delete(self.base_url + url, params=params)


class RpSlaClient(BaseClient):
    def __init__(self, base_url):
        super().__init__(base_url)

    def health_check(self):
        response = self.get("/")
        return response.status_code == 200 and response.json() == {"Service": "RP_SLA"}

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
        response = self.post("/instances/new_from_config", params={"filename": filename})
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

    def get_configured_routes(self, instance_id):
        response = self.get(f"/instances/{instance_id}/routes/configured")
        response.raise_for_status()
        return response.json()

    def get_best_routes(self, instance_id):
        response = self.get(f"/instances/{instance_id}/best_routes")
        response.raise_for_status()
        return response.json()

    def evaluate_routes(self, instance_id):
        response = self.post(f"/instances/{instance_id}/evaluate_routes")
        response.raise_for_status()
        return response.json()
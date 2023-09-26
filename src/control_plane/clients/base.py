import requests


class BaseClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, url, params=None):
        return self.session.get(self.base_url + url, params=params)

    def post(self, url, params=None, data=None, json=None):
        return self.session.post(
            self.base_url + url, params=params, data=data, json=json
        )

    def put(self, url, params=None, data=None):
        return self.session.put(self.base_url + url, params=params, data=data)

    def delete(self, url, params=None):
        return self.session.delete(self.base_url + url, params=params)

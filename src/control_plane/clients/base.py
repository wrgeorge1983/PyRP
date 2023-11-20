import requests
import aiohttp


class BaseClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.requests_session = requests.Session()

    def get(self, url, params=None) -> requests.Response:
        return self.requests_session.get(self.base_url + url, params=params)

    async def aget(self, url, params=None):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url + url, params=params) as response:
                response.raise_for_status()
                return await response.json()

    def post(self, url, params=None, data=None, json=None) -> requests.Response:
        return self.requests_session.post(
            self.base_url + url, params=params, data=data, json=json
        )

    async def apost(self, url, params=None, data=None, json=None):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url + url, params=params, data=data, json=json
            ) as response:
                response.raise_for_status()
                return await response.json()

    def put(self, url, params=None, data=None) -> requests.Response:
        return self.requests_session.put(self.base_url + url, params=params, data=data)

    async def aput(self, url, params=None, data=None):
        async with aiohttp.ClientSession() as session:
            async with session.put(
                self.base_url + url, params=params, data=data
            ) as response:
                response.raise_for_status()
                return await response.json()

    def delete(self, url, params=None) -> requests.Response:
        return self.requests_session.delete(self.base_url + url, params=params)

    async def adelete(self, url, params=None):
        async with aiohttp.ClientSession() as session:
            async with session.delete(self.base_url + url, params=params) as response:
                response.raise_for_status()
                return await response.json()

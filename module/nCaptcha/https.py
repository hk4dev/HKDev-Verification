import aiohttp
import asyncio

from .requests import Api


class HttpClient:
    def __init__(
            self,
            client_id: str, client_secret: str,
            session: aiohttp.ClientSession = None,
            loop: asyncio.AbstractEventLoop = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.requests = Api(
            id=self.client_id,
            secret=self.client_secret,
            loop=loop,
            session=session
        )

    async def _get_key(self, path, code: int, **kwargs):
        if code == 0:
            params = {"code": 0}
        elif code == 1:
            params = {
                "code": 1,
                "key": kwargs.get("key"),
                "value": kwargs.get("value")
            }
        else:
            raise ValueError("Code values can only be given 0 and 1.")
        return await self.requests.get("/captcha/{0}".format(path), params=params)

    async def _get_source(self, path, key: str):
        return await self.requests.get("/captcha/{0}".format(path), params={"key": key})

    async def image_key(self, code: int, key: str = None, value: str = None):
        return await self._get_key(path="nkey", code=code, key=key, value=value)

    async def sound_key(self, code: int, key: str = None, value: str = None):
        return await self._get_key(path="skey", code=code, key=key, value=value)

    async def image_get(self, key: str):
        return await self._get_source(path="ncaptcha.bin", key=key)

    async def sound_get(self, key: str):
        return await self._get_source(path="scaptcha", key=key)

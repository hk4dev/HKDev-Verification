import time
import json
import aiohttp
import asyncio
import logging

from .errors import *

log = logging.getLogger(__name__)


class Api:
    def __init__(
            self,
            id: str, secret: str,
            session: aiohttp.ClientSession = None,
            loop: asyncio.AbstractEventLoop = None,
            refresh_session: int = 300
    ):
        self.BASE = "https://openapi.naver.com/v1"
        self.id = id
        self.secret = secret

        self.header = {
            "X-Naver-Client-Id": self.id,
            "X-Naver-Client-Secret": self.secret
        }

        self.loop = loop
        if session is not None:
            self.session = session
        else:
            self.session = aiohttp.ClientSession(loop=self.loop)
        self._session_start = time.time()
        self.refresh_session_period = refresh_session

    async def close(self):
        await self.session.close()

    async def refresh_session(self):
        await self.session.close()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self._session_start = time.time()

    async def get_session(self):
        if not self.session:
            await self.refresh_session()
        elif 0 <= self.refresh_session_period <= time.time() - self._session_start:
            await self.refresh_session()
        return self.session

    async def requests(self, method: str, path: str, **kwargs):
        url = "{}{}".format(self.BASE, path)

        if "headers" not in kwargs:
            kwargs['headers'] = self.header
        else:
            kwargs['headers'].update(self.header)

        session = await self.get_session()
        async with session.request(method, url, **kwargs) as response:
            if response.content_type == "application/json":
                data = await response.json()
            elif response.content_type.startswith("image/"):
                data = await response.read()
            elif response.content_type.startswith("audio/"):
                data = await response.read()
            else:
                fp_data = await response.text()
                data = json.loads(fp_data)
            log.debug(f'{method} {url} returned {response.status}')
            if 200 <= response.status < 300:
                return data
            elif response.status == 500:
                raise CaptchaSystemError(response, data)
            elif response.status == 400:
                raise UnissuedSource(response, data)
            elif response.status == 403:
                raise InvalidKey(response, data)
            else:
                raise HTTPException(response, data)

    async def get(self, path: str, **kwargs):
        return await self.requests("GET", path, **kwargs)

import aiohttp
import asyncio

from .https import HttpClient
from .verificationType import VerificationType


class Client:
    def __init__(
            self,
            client_id: str, client_secret: str,
            session: aiohttp.ClientSession = None,
            loop: asyncio.AbstractEventLoop = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.http = HttpClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            loop=loop,
            session=session
        )

        self.last_key = None
        self.verification_type = None

    async def get_image(self):
        self.verification_type = VerificationType.image
        code_result = await self.http.image_key(code=0)
        self.last_key = code_result.get("key")
        return await self.http.image_get(key=self.last_key)

    async def refresh_image(self, key: str = None):
        if key is None:
            key = self.last_key
        return await self.http.image_get(key=key)

    async def get_sound(self):
        self.verification_type = VerificationType.sound
        code_result = await self.http.sound_key(code=0)
        self.last_key = code_result.get("key")
        return await self.http.sound_get(key=self.last_key)

    async def refresh_sound(self, key: str = None):
        if key is None:
            key = self.last_key
        return await self.http.sound_get(key=key)

    async def verification(self, value: str, key: str = None, verification_type: VerificationType = None):
        if verification_type is None:
            verification_type = self.verification_type
        if key is None:
            key = self.last_key

        if verification_type == VerificationType.image:
            return await self.http.image_key(code=1, key=key, value=value)
        elif verification_type == VerificationType.sound:
            return await self.http.sound_key(code=1, key=key, value=value)

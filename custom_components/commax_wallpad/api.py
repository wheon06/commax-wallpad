"""Async HTTP-forward-proxy client. Does not log credentials or SOAP bodies."""

import asyncio
import base64

import aiohttp

from .const import DEFAULT_TIMEOUT_SECONDS
from .models import ConnectionConfig
from .protocol import (
    MAX_RESPONSE_BYTES,
    AuthenticationError,
    ConnectionError,
    ProtocolError,
    get_request,
    parse_light,
    parse_response,
    set_request,
)


class CommaxClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        config: ConnectionConfig,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._session = session
        self._config = config
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._auth = (
            "Basic "
            + base64.b64encode(f"{config.proxy_username}:{config.proxy_password}".encode()).decode()
        )

    async def _request(self, payload: bytes) -> bytes:
        try:
            async with self._session.post(
                self._config.target_url,
                proxy=self._config.proxy_url,
                data=payload,
                timeout=self._timeout,
                allow_redirects=False,
                headers={
                    "Proxy-Authorization": self._auth,
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": '""',
                    "Connection": "close",
                    "User-Agent": "gSOAP/2.7",
                },
            ) as response:
                if response.status in (401, 403, 407):
                    raise AuthenticationError("Proxy authentication failed")
                if response.status != 200:
                    raise ConnectionError("Unexpected proxy HTTP status")
                content = bytearray()
                async for chunk in response.content.iter_chunked(16384):
                    content.extend(chunk)
                    if len(content) > MAX_RESPONSE_BYTES:
                        raise ProtocolError("SOAP response exceeds size limit")
                return bytes(content)
        except aiohttp.ClientHttpProxyError as error:
            if error.status in (401, 403, 407):
                raise AuthenticationError("Proxy authentication failed") from None
            raise ConnectionError("HTTP proxy connection failed") from None
        except (aiohttp.ClientError, OSError, asyncio.TimeoutError):
            raise ConnectionError("COMMAX connection failed or timed out") from None

    async def get_light(self, order: int) -> bool:
        return parse_light(await self._request(get_request(order)), order)

    async def set_light(self, order: int, on: bool) -> None:
        parse_response(await self._request(set_request(order, on)), "setLightResponse")

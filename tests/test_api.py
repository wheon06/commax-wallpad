import asyncio

import aiohttp
import pytest

from custom_components.commax_wallpad.api import CommaxClient
from custom_components.commax_wallpad.models import ConnectionConfig
from custom_components.commax_wallpad.protocol import (
    AuthenticationError,
    ConnectionError,
    ProtocolError,
)

from .conftest import CONNECTION
from .test_protocol import state_reply


@pytest.fixture
async def raw_proxy(socket_enabled):
    data = {"status": 200, "body": state_reply(), "requests": []}

    async def handle(reader, writer):
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            lines = head.decode().split("\r\n")
            headers = dict(line.split(": ", 1) for line in lines[1:] if ": " in line)
            body = await reader.readexactly(int(headers.get("Content-Length", 0)))
            data["requests"].append((lines[0], headers, body))
            payload = data["body"]
            writer.write(
                f"HTTP/1.0 {data['status']} Test\r\nContent-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
                + payload
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    data["url"] = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    yield data
    server.close()
    await server.wait_closed()


async def test_real_http_forward_proxy(raw_proxy):
    config = ConnectionConfig.from_mapping({**CONNECTION, "proxy_url": raw_proxy["url"]})
    async with aiohttp.ClientSession() as session:
        assert await CommaxClient(session, config).get_light(6) is True
    line, headers, body = raw_proxy["requests"][0]
    assert line == "POST http://10.0.0.10:29700 HTTP/1.1"
    assert headers["Proxy-Authorization"] == "Basic Zml4dHVyZS11c2VyOmZpeHR1cmUtcGFzc3dvcmQ="
    assert headers["Host"] == "10.0.0.10:29700"
    assert b"<order>6</order>" in body


@pytest.mark.parametrize(
    "status,error",
    [
        (407, AuthenticationError),
        (403, AuthenticationError),
        (302, ConnectionError),
        (502, ConnectionError),
    ],
)
async def test_http_errors_are_sanitized(raw_proxy, status, error):
    raw_proxy.update(status=status, body=b"fixture-password")
    config = ConnectionConfig.from_mapping({**CONNECTION, "proxy_url": raw_proxy["url"]})
    async with aiohttp.ClientSession() as session:
        with pytest.raises(error) as caught:
            await CommaxClient(session, config).get_light(6)
    assert "fixture-password" not in str(caught.value)


async def test_response_size_is_bounded(raw_proxy):
    raw_proxy["body"] = b"x" * 262145
    config = ConnectionConfig.from_mapping({**CONNECTION, "proxy_url": raw_proxy["url"]})
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ProtocolError):
            await CommaxClient(session, config).get_light(6)

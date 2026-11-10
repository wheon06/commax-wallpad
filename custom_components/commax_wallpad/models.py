"""Validated connection settings and channel state; no Home Assistant dependencies."""

import hashlib
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .const import CONNECTION_KEYS, MAX_CHANNEL_NUMBER, MAX_CHANNELS


def validate_http_url(value: str, *, proxy: bool = False) -> str:
    """Reject ambiguous URLs and header injection before any network request."""
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("A complete HTTP URL is required")
    url = urlsplit(value)
    if (
        url.scheme != "http"
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.fragment
        or url.port == 0
    ):
        raise ValueError("Use an HTTP URL without embedded credentials or fragments")
    if proxy and (url.path not in ("", "/") or url.query):
        raise ValueError("Proxy URL cannot include a path or query")
    # Accessing .port also validates the range; canonicalize host casing.
    host = url.hostname.encode("idna").decode().lower()
    host = f"[{host}]" if ":" in host else host
    port = f":{url.port}" if url.port and url.port != 80 else ""
    return urlunsplit(("http", host + port, "" if proxy else url.path, url.query, ""))


@dataclass(frozen=True)
class ConnectionConfig:
    proxy_url: str = field(repr=False)
    target_url: str = field(repr=False)
    proxy_username: str = field(repr=False)
    proxy_password: str = field(repr=False)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "ConnectionConfig":
        user, password = value["proxy_username"], value["proxy_password"]
        if (
            not isinstance(user, str)
            or not user
            or ":" in user
            or not isinstance(password, str)
            or not password
            or any(c in user + password for c in "\r\n\x00")
        ):
            raise ValueError("Valid proxy credentials are required")
        return cls(
            validate_http_url(value["proxy_url"], proxy=True),
            validate_http_url(value["target_url"]),
            user,
            password,
        )

    def as_dict(self) -> dict[str, str]:
        return {key: getattr(self, key) for key in CONNECTION_KEYS}

    @property
    def identity(self) -> str:
        return hashlib.sha256(f"{self.proxy_url}|{self.target_url}".encode()).hexdigest()[:24]


@dataclass(frozen=True)
class ChannelState:
    is_on: bool | None
    available: bool = True


def validate_order(order: int) -> None:
    if (
        isinstance(order, bool)
        or not isinstance(order, int)
        or not 1 <= order <= MAX_CHANNEL_NUMBER
    ):
        raise ValueError("Channel must be a positive integer up to 65535")


def parse_orders(value: str) -> list[int]:
    """Parse explicit IDs and short ranges. Never probe unspecified channels."""
    if not isinstance(value, str):
        raise ValueError("Channel list must be text")
    result: list[int] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            ends = token.split("-")
            if len(ends) != 2:
                raise ValueError("Invalid channel range")
            start, end = (int(x.strip()) for x in ends)
            validate_order(start)
            validate_order(end)
            if start > end or end - start + 1 > MAX_CHANNELS:
                raise ValueError("Invalid or excessive channel range")
            numbers = list(range(start, end + 1))
        else:
            numbers = [int(token)]
        for number in numbers:
            validate_order(number)
            if number in result:
                raise ValueError("Duplicate channel")
            result.append(number)
            if len(result) > MAX_CHANNELS:
                raise ValueError("Too many channels")
    return result


def validate_channels(lights: str, fans: str) -> tuple[list[int], list[int]]:
    light_ids, fan_ids = parse_orders(lights), parse_orders(fans)
    if not light_ids + fan_ids or set(light_ids) & set(fan_ids):
        raise ValueError("Select at least one channel without overlapping types")
    if len(light_ids) + len(fan_ids) > MAX_CHANNELS:
        raise ValueError("Too many channels")
    return light_ids, fan_ids

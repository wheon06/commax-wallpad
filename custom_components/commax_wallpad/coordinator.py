"""Serialize polling and control; report observed state, never optimistic state."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CommaxClient
from .const import CONF_FANS, CONF_LIGHTS, CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS
from .models import ChannelState, validate_channels
from .protocol import AuthenticationError, ConnectionError, ProtocolError

_LOGGER = logging.getLogger(__name__)


class CommaxCoordinator(DataUpdateCoordinator[dict[int, ChannelState]]):
    def __init__(self, hass, entry, client: CommaxClient) -> None:
        settings = {**entry.data, **entry.options}
        self.lights, self.fans = validate_channels(settings[CONF_LIGHTS], settings[CONF_FANS])
        self.orders = self.lights + self.fans
        self.client = client
        self.lock = asyncio.Lock()
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="COMMAX Wallpad",
            update_interval=timedelta(
                seconds=settings.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS)
            ),
            always_update=False,
        )

    async def _async_update_data(self) -> dict[int, ChannelState]:
        results: dict[int, ChannelState] = {}
        try:
            async with self.lock:
                # Bound each complete poll, even with many configured channels.
                async with asyncio.timeout(30):
                    for order in self.orders:
                        try:
                            results[order] = ChannelState(await self.client.get_light(order))
                        except ProtocolError:
                            results[order] = ChannelState(None, available=False)
        except AuthenticationError:
            raise ConfigEntryAuthFailed("COMMAX proxy credentials were rejected") from None
        except (ConnectionError, TimeoutError):
            raise UpdateFailed("COMMAX connection unavailable") from None
        if not any(item.available for item in results.values()):
            raise UpdateFailed("No configured COMMAX channel could be read")
        return results

    def _publish(self, order: int, state: ChannelState) -> None:
        self.async_set_updated_data({**(self.data or {}), order: state})

    async def async_control(self, order: int, on: bool) -> None:
        if order not in self.orders:
            raise HomeAssistantError("Channel is not configured")
        async with self.lock:
            try:
                # Never automatically resend a physical command.
                await self.client.set_light(order, on)
                for _ in range(5):
                    await asyncio.sleep(1)
                    actual = await self.client.get_light(order)
                    self._publish(order, ChannelState(actual))
                    if actual == on:
                        return
            except AuthenticationError:
                self._publish(order, ChannelState(None, available=False))
                self.config_entry.async_start_reauth(self.hass)
                raise HomeAssistantError("COMMAX proxy requires reauthentication") from None
            except (ConnectionError, ProtocolError):
                self._publish(order, ChannelState(None, available=False))
                raise HomeAssistantError("COMMAX state could not be confirmed") from None
        raise HomeAssistantError("COMMAX power state did not change after five checks")

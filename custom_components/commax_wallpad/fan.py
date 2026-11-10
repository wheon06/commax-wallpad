"""Exhaust fans controlled through binary lighting channels."""

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .entity import CommaxEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    async_add_entities(CommaxFan(coordinator, entry, order) for order in coordinator.fans)


class CommaxFan(CommaxEntity, FanEntity):
    _attr_translation_key = "fan"
    _attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        await self.coordinator.async_control(self.order, True)

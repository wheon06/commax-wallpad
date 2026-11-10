"""Binary lighting channels."""

from homeassistant.components.light import ColorMode, LightEntity

from .entity import CommaxEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    async_add_entities(CommaxLight(coordinator, entry, order) for order in coordinator.lights)


class CommaxLight(CommaxEntity, LightEntity):
    _attr_translation_key = "light"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

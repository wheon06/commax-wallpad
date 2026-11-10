"""Allowlisted diagnostics: never export endpoints, credentials, names or XML."""

from .const import CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS


async def async_get_config_entry_diagnostics(hass, entry) -> dict:
    coordinator = entry.runtime_data
    settings = {**entry.data, **entry.options}
    return {
        "entry_version": entry.version,
        "poll_seconds": settings.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS),
        "light_channels": coordinator.lights,
        "fan_channels": coordinator.fans,
        "last_update_success": coordinator.last_update_success,
        "channels": {
            str(order): {"available": state.available}
            for order, state in (coordinator.data or {}).items()
        },
    }

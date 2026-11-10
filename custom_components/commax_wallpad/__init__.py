"""Home Assistant setup and migration for COMMAX Wallpad."""

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CommaxClient
from .coordinator import CommaxCoordinator
from .models import ConnectionConfig
from .registry import async_remove_stale_entities

PLATFORMS = [Platform.LIGHT, Platform.FAN]


async def async_setup_entry(hass, entry) -> bool:
    try:
        config = ConnectionConfig.from_mapping(entry.data)
        coordinator = CommaxCoordinator(
            hass, entry, CommaxClient(async_get_clientsession(hass), config)
        )
    except (ValueError, KeyError, TypeError):
        raise ConfigEntryError("Invalid COMMAX connection or channel configuration") from None
    await coordinator.async_config_entry_first_refresh()
    async_remove_stale_entities(hass, entry, coordinator)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass, entry) -> bool:
    """Keep v0.1 endpoint identity and entity IDs so Apple Home rooms survive."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        hass.config_entries.async_update_entry(entry, version=2)
    return True

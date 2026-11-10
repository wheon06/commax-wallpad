"""Remove only stale channel entities owned by this COMMAX config entry."""

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


def async_remove_stale_entities(hass, entry, coordinator) -> None:
    registry = er.async_get(hass)
    expected = {
        (domain, f"{entry.unique_id}_channel_{order}")
        for domain, orders in (("light", coordinator.lights), ("fan", coordinator.fans))
        for order in orders
    }
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform != DOMAIN:
            continue
        if (entity.domain, entity.unique_id) not in expected:
            registry.async_remove(entity.entity_id)

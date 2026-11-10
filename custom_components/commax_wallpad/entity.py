"""Shared entity behavior with stable channel identifiers."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CommaxCoordinator
from .models import ChannelState


class CommaxEntity(CoordinatorEntity[CommaxCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, order: int) -> None:
        super().__init__(coordinator)
        self.order = order
        # Exact legacy ID format is deliberately preserved.
        self._attr_unique_id = f"{entry.unique_id}_channel_{order}"
        self._attr_translation_placeholders = {"channel": str(order)}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="COMMAX Wallpad",
            manufacturer="COMMAX",
            model="SOAP / RS-485 gateway",
        )
        self._attr_extra_state_attributes = {"commax_order": order}

    @property
    def available(self) -> bool:
        state = self.coordinator.data.get(self.order)
        return super().available and state is not None and state.available

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self.order, ChannelState(None, False)).is_on

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_control(self.order, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_control(self.order, False)

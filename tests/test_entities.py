from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import STATE_OFF
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.commax_wallpad.diagnostics import async_get_config_entry_diagnostics
from custom_components.commax_wallpad.models import ChannelState
from custom_components.commax_wallpad.protocol import ConnectionError

from .conftest import DOMAIN


async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities_and_unload(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    states = hass.states.async_all()
    assert sum(s.domain == "light" for s in states) == 2
    assert sum(s.domain == "fan" for s in states) == 2
    assert all(s.state == STATE_OFF for s in states if s.domain in ("light", "fan"))
    assert await hass.config_entries.async_unload(config_entry.entry_id)


async def test_type_change_removes_old_entity_only(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    registry = er.async_get(hass)
    old_id = registry.async_get_entity_id("light", DOMAIN, "fixture-wallpad_channel_6")
    unchanged_id = registry.async_get_entity_id("light", DOMAIN, "fixture-wallpad_channel_1")
    registry.async_update_entity(unchanged_id, name="My unchanged light")
    hass.config_entries.async_update_entry(
        config_entry, options={"lights": "1", "fans": "6,15,18", "poll_seconds": 30}
    )
    await hass.async_block_till_done()
    assert registry.async_get(old_id) is None
    assert registry.async_get_entity_id("fan", DOMAIN, "fixture-wallpad_channel_6") is not None
    assert registry.async_get(unchanged_id).name == "My unchanged light"
    assert config_entry.runtime_data.fans == [6, 15, 18]


async def test_control_checks_actual_state(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    mock_client[0].side_effect = [False, True]
    with patch(
        "custom_components.commax_wallpad.coordinator.asyncio.sleep", new_callable=AsyncMock
    ):
        await coordinator.async_control(6, True)
    mock_client[1].assert_awaited_once_with(6, True)
    assert coordinator.data[6] == ChannelState(True)


async def test_failed_fan_never_reports_on(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    with patch(
        "custom_components.commax_wallpad.coordinator.asyncio.sleep", new_callable=AsyncMock
    ):
        with pytest.raises(HomeAssistantError):
            await coordinator.async_control(15, True)
    mock_client[1].assert_awaited_once_with(15, True)
    assert coordinator.data[15] == ChannelState(False)


async def test_unconfigured_channel_never_sent(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    with pytest.raises(HomeAssistantError):
        await config_entry.runtime_data.async_control(999, True)
    mock_client[1].assert_not_called()


async def test_poll_failure_stops_early(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    mock_client[0].reset_mock()
    mock_client[0].side_effect = ConnectionError("offline")
    await config_entry.runtime_data.async_refresh()
    assert not config_entry.runtime_data.last_update_success
    assert mock_client[0].await_count == 1


async def test_diagnostics_do_not_include_connection_or_state(hass, config_entry, mock_client):
    await setup(hass, config_entry)
    data = await async_get_config_entry_diagnostics(hass, config_entry)
    text = str(data)
    for secret in [
        "fixture-user",
        "fixture-password",
        "192.0.2.10",
        "10.0.0.10",
        "proxy_url",
        "is_on",
    ]:
        assert secret not in text

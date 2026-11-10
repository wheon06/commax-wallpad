from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.commax_wallpad.protocol import AuthenticationError

from .conftest import CONNECTION, DOMAIN, SETTINGS


async def start_manual(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )


async def test_user_flow(hass, mock_client):
    result = await start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert result["step_id"] == "channels"
    with patch("custom_components.commax_wallpad.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], SETTINGS)
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {**CONNECTION, **SETTINGS}


async def test_no_household_defaults(hass):
    result = await start_manual(hass)
    serialized = str(result["data_schema"].schema)
    assert "fixture-password" not in serialized
    assert "192.0.2.10" not in serialized


async def test_overlap_is_rejected(hass, mock_client):
    result = await start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**SETTINGS, "fans": "6"}
    )
    assert result["errors"] == {"base": "invalid_channels"}
    mock_client[0].assert_not_called()


async def test_invalid_auth(hass, mock_client):
    mock_client[0].side_effect = AuthenticationError("rejected")
    result = await start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], SETTINGS)
    assert result["errors"] == {"base": "invalid_auth"}


async def test_duplicate_legacy_identity(hass, config_entry, mock_client):
    result = await start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], SETTINGS)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_move_light_to_fan(hass, config_entry, mock_client):
    with patch("custom_components.commax_wallpad.async_reload_entry", new_callable=AsyncMock):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"lights": "1", "fans": "6,15,18", "poll_seconds": 45}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options["fans"] == "6,15,18"


async def test_legacy_file_missing(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "legacy"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "missing_connection"}


async def test_reauth(hass, config_entry, mock_client):
    with patch("homeassistant.config_entries.ConfigEntries.async_reload", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_REAUTH, "entry_id": config_entry.entry_id},
            data=config_entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"proxy_username": "new-user", "proxy_password": "new-secret"}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.ABORT
    assert config_entry.data["proxy_password"] == "new-secret"
    assert config_entry.unique_id == "fixture-wallpad"


async def test_migrate_v1_keeps_identity(hass, mock_client):
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, unique_id="old-identity", data={**CONNECTION, **SETTINGS}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.version == 2
    assert entry.unique_id == "old-identity"
    assert entry.data["fans"] == "15,18"

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "commax_wallpad"
CONNECTION = {
    "proxy_url": "http://192.0.2.10:30128",
    "target_url": "http://10.0.0.10:29700",
    "proxy_username": "fixture-user",
    "proxy_password": "fixture-password",
}
SETTINGS = {"lights": "1,6", "fans": "15,18", "poll_seconds": 30}


@pytest.fixture(autouse=True)
def enable_integration(enable_custom_integrations):
    yield


@pytest.fixture
def config_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="COMMAX Wallpad",
        version=2,
        unique_id="fixture-wallpad",
        data={**CONNECTION, **SETTINGS},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_client():
    with (
        patch(
            "custom_components.commax_wallpad.api.CommaxClient.get_light", new_callable=AsyncMock
        ) as get,
        patch(
            "custom_components.commax_wallpad.api.CommaxClient.set_light", new_callable=AsyncMock
        ) as set_,
    ):
        get.return_value = False
        yield get, set_

"""Fixtures backed by Home Assistant's official pytest plugin."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.pushie.api import PushieClient


@pytest.fixture
def hass_config_dir(hass_tmp_config_dir):
    """Keep each test's HA configuration isolated and writable."""
    return hass_tmp_config_dir


@pytest.fixture
def mock_pushie_client():
    """Mock the external Pushie service; use real HA flows and entities."""
    client = AsyncMock(spec=PushieClient)
    client.url = "https://push.example"
    client.topics.return_value = {"automation": "Automation", "backup": "Backup"}
    client.send.return_value = {"notificationId": "test-id", "queued": 2, "inboxUsers": 1}
    with (
        patch("custom_components.pushie.PushieClient", return_value=client),
        patch("custom_components.pushie.config_flow.PushieClient", return_value=client),
    ):
        yield client


@pytest.fixture
def config_entry():
    return MockConfigEntry(
        domain="pushie",
        title="Pushie",
        data={
            "url": "https://push.example",
            "token": "test-token",
            "installation_id": "installation",
        },
        options={"topics": ["automation"]},
    )

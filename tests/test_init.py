"""Real configuration-entry setup, errors, and unloading."""

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.pushie.api import PushieError


async def test_setup_and_unload(hass, config_entry, mock_pushie_client):
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("notify.pushie_automation") is not None
    mock_pushie_client.verify.assert_awaited_once()
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get("notify.pushie_automation").state == "unavailable"


@pytest.mark.parametrize(
    ("error", "state"),
    [
        ("invalid_auth", ConfigEntryState.SETUP_ERROR),
        ("cannot_connect", ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_errors(hass, config_entry, mock_pushie_client, error, state):
    mock_pushie_client.verify.side_effect = PushieError(error)
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is state
    assert hass.states.get("notify.pushie_automation") is None

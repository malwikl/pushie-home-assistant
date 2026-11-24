"""Exercise registered notify entities through HA services and registries."""

from homeassistant.helpers import entity_registry as er


async def setup_notify(hass, config_entry):
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_notify_service_uses_selected_topic(hass, config_entry, mock_pushie_client):
    await setup_notify(hass, config_entry)
    await hass.services.async_call(
        "notify",
        "send_message",
        {"entity_id": "notify.pushie_automation", "message": "Door opened", "title": "House"},
        blocking=True,
    )
    mock_pushie_client.send.assert_awaited_once_with("automation", "Door opened", "House")
    assert hass.states.get("notify.pushie_backup") is None


async def test_removed_topic_recovers_same_entity(hass, config_entry, mock_pushie_client):
    await setup_notify(hass, config_entry)
    registry = er.async_get(hass)
    identity = registry.async_get("notify.pushie_automation").unique_id
    mock_pushie_client.topics.return_value = {}
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("notify.pushie_automation").state == "unavailable"
    mock_pushie_client.topics.return_value = {"automation": "Renamed"}
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("notify.pushie_automation").state != "unavailable"
    assert registry.async_get("notify.pushie_automation").unique_id == identity

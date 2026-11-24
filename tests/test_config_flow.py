"""Run Pushie's configuration flows through the real HA flow manager."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pushie.api import PushieError


async def test_setup_selects_topics_without_sending(hass, mock_pushie_client):
    result = await hass.config_entries.flow.async_init(
        "pushie", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": "https://push.example", "token": "test-token"}
    )
    assert result["step_id"] == "topics"
    mock_pushie_client.verify.assert_awaited_once()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"topics": ["automation"]}
    )
    assert result["type"] is FlowResultType.MENU
    mock_pushie_client.send.assert_not_called()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"topics": ["automation"]}
    assert result["data"]["installation_id"]
    await hass.async_block_till_done()


async def test_invalid_auth_stays_on_user_form(hass, mock_pushie_client):
    mock_pushie_client.verify.side_effect = PushieError("invalid_auth", 401)
    result = await hass.config_entries.flow.async_init(
        "pushie",
        context={"source": config_entries.SOURCE_USER},
        data={"url": "https://push.example", "token": "bad-token"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    mock_pushie_client.send.assert_not_called()


async def test_duplicate_server_aborts(hass, config_entry, mock_pushie_client):
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "pushie",
        context={"source": config_entries.SOURCE_USER},
        data={"url": "https://push.example", "token": "test-token"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_real_test_only_sends_on_submission(hass, mock_pushie_client):
    result = await hass.config_entries.flow.async_init(
        "pushie",
        context={"source": config_entries.SOURCE_USER},
        data={"url": "https://push.example", "token": "test-token"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"topics": ["automation"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "test"}
    )
    assert result["step_id"] == "test"
    mock_pushie_client.send.assert_not_called()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"topic": "automation", "title": "Test", "notification": "Hello"},
    )
    assert result["step_id"] == "result"
    mock_pushie_client.send.assert_awaited_once_with("automation", "Hello", "Test")


async def test_options_verify_does_not_send(hass, config_entry, mock_pushie_client):
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "verify"}
    )
    assert result["step_id"] == "result"
    mock_pushie_client.send.assert_not_called()

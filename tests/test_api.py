import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses

spec = importlib.util.spec_from_file_location(
    "pushie_api", Path(__file__).parents[1] / "custom_components/pushie/api.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


@pytest.mark.parametrize(
    "url", ["http://host", "https://user:pass@host", "https://host/path", "https://host?q=x"]
)
def test_url_rejects_unsafe_origins(url):
    with pytest.raises(api.PushieError):
        api.normalize_url(url)


@pytest.mark.asyncio
async def test_retry_preserves_key_and_payload():
    with aioresponses() as mock:
        mock.post("https://push.example/api/send", status=503)
        mock.post("https://push.example/api/send", payload={"queued": 2, "inboxUsers": 1})
        async with aiohttp.ClientSession() as session:
            client = api.PushieClient(session, "https://push.example/", "secret")
            with patch.object(api.asyncio, "sleep", new=AsyncMock()):
                assert (await client.send("automation", 'Hi "世界"\nOK'))["queued"] == 2
        calls = next(iter(mock.requests.values()))
        assert len(calls) == 2
        assert (
            calls[0].kwargs["headers"]["Idempotency-Key"]
            == calls[1].kwargs["headers"]["Idempotency-Key"]
        )
        assert calls[0].kwargs["json"] == calls[1].kwargs["json"]
        assert set(calls[0].kwargs["json"]) == {"topic", "title", "body"}


@pytest.mark.asyncio
async def test_verify_never_sends():
    with aioresponses() as mock:
        mock.post(
            "https://push.example/api/verify",
            payload={
                "ok": True,
                "apiVersion": 1,
                "capabilities": ["verify", "topics:list", "topics:send"],
            },
        )
        async with aiohttp.ClientSession() as session:
            await api.PushieClient(session, "https://push.example", "secret").verify()
        assert len(mock.requests) == 1


@pytest.mark.asyncio
async def test_message_limits_before_network():
    client = api.PushieClient(None, "https://push.example", "secret")
    for message in [" ", "世" * 667]:
        with pytest.raises(api.PushieError, match="invalid_message"):
            await client.send("automation", message)


@pytest.mark.asyncio
async def test_auth_not_retried():
    with aioresponses() as mock:
        mock.post("https://push.example/api/send", status=401)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(api.PushieError, match="invalid_auth"):
                await api.PushieClient(session, "https://push.example", "secret").send("a", "hello")
        assert len(next(iter(mock.requests.values()))) == 1


def test_home_assistant_imports():
    import sys

    sys.path.insert(0, str(Path(__file__).parents[1]))
    from custom_components.pushie import config_flow, notify

    assert config_flow.PushieConfigFlow.VERSION == 1
    assert notify.PushieNotify._attr_supported_features


@pytest.mark.asyncio
async def test_topics_flow_verifies_before_creation():
    from custom_components.pushie.config_flow import PushieConfigFlow

    flow = PushieConfigFlow()
    flow.hass = object()
    client = AsyncMock()
    client.url = "https://push.example"
    with (
        patch.object(flow, "client", return_value=client),
        patch.object(flow, "_async_current_entries", return_value=[]),
        patch.object(
            flow, "async_step_topics", new=AsyncMock(return_value={"type": "form"})
        ) as topics,
    ):
        result = await flow.async_step_user({"url": "https://push.example", "token": "secret"})
    client.verify.assert_awaited_once()
    topics.assert_awaited_once()
    client.send.assert_not_called()
    assert result["type"] == "form"


@pytest.mark.asyncio
async def test_test_form_does_not_send_until_submission():
    from custom_components.pushie.config_flow import PushieConfigFlow

    flow = PushieConfigFlow()
    flow.selected = ["automation"]
    client = AsyncMock()
    with (
        patch.object(flow, "client", return_value=client),
        patch.object(flow, "async_show_form", return_value={}) as form,
    ):
        await flow.async_step_test()
    client.send.assert_not_called()
    assert form.call_args.kwargs["step_id"] == "test"


@pytest.mark.asyncio
async def test_removed_topic_entity_recovers_identity():
    from unittest.mock import MagicMock

    from custom_components.pushie.notify import PushieNotify

    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"automation": "Automation"}
    entry = MagicMock()
    entry.data = {"installation_id": "persisted"}
    entity = PushieNotify(coordinator, entry, "automation")
    identity = entity.unique_id
    assert entity.available
    coordinator.data = {}
    assert not entity.available
    coordinator.data = {"automation": "Renamed description"}
    assert entity.available and entity.unique_id == identity

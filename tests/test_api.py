"""Exercise HTTPS requests using HA's aiohttp fixtures."""

from unittest.mock import AsyncMock, patch

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMockResponse

from custom_components.pushie import api


@pytest.mark.parametrize(
    "url", ["http://host", "https://user:pass@host", "https://host/path", "https://host?q=x"]
)
def test_url_rejects_unsafe_origins(url):
    with pytest.raises(api.PushieError):
        api.normalize_url(url)


async def test_retry_preserves_key_and_payload(hass, aioclient_mock):
    attempts = 0

    async def reply(method, url, data):
        nonlocal attempts
        attempts += 1
        return AiohttpClientMockResponse(
            method,
            url,
            status=503 if attempts == 1 else 200,
            json={"queued": 2, "inboxUsers": 1},
        )

    aioclient_mock.request("post", "https://push.example/api/send", side_effect=reply)
    client = api.PushieClient(async_get_clientsession(hass), "https://push.example/", "secret")
    with patch.object(api.asyncio, "sleep", new=AsyncMock()):
        assert (await client.send("automation", 'Hi "世界"\nOK'))["queued"] == 2
    first, second = aioclient_mock.mock_calls
    assert first[3]["Idempotency-Key"] == second[3]["Idempotency-Key"]
    assert first[2] == second[2]
    assert set(first[2]) == {"topic", "title", "body"}


async def test_verify_never_sends(hass, aioclient_mock):
    aioclient_mock.post(
        "https://push.example/api/verify",
        json={
            "ok": True,
            "apiVersion": 1,
            "capabilities": ["verify", "topics:list", "topics:send"],
        },
    )
    await api.PushieClient(async_get_clientsession(hass), "https://push.example", "secret").verify()
    assert aioclient_mock.call_count == 1


async def test_notification_limits_before_network():
    client = api.PushieClient(None, "https://push.example", "secret")
    for notification in [" ", "世" * (256 * 1024 // 3 + 1)]:
        with pytest.raises(api.PushieError, match="invalid_notification"):
            await client.send("automation", notification)


async def test_auth_not_retried(hass, aioclient_mock):
    aioclient_mock.post("https://push.example/api/send", status=401)
    with pytest.raises(api.PushieError, match="invalid_auth"):
        await api.PushieClient(
            async_get_clientsession(hass), "https://push.example", "secret"
        ).send("a", "hello")
    assert aioclient_mock.call_count == 1


async def test_full_notification_uses_standard_body():
    client = api.PushieClient(None, "https://push.example", "secret")
    client.request = AsyncMock(return_value={"queued": 1})
    notification = "x" * (256 * 1024)
    await client.send("automation", notification)
    assert client.request.call_args.args[2] == {
        "topic": "automation",
        "title": "Home Assistant",
        "body": notification,
    }

"""Small topic-only Pushie client. Never log credentials or message contents."""

import asyncio
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from uuid import uuid4

import aiohttp


class PushieError(Exception):
    def __init__(self, code, status=0):
        self.code, self.status = code, status
        super().__init__(code)


def normalize_url(value):
    try:
        parsed = urlsplit(value.strip())
        _ = parsed.port
    except ValueError as err:
        raise PushieError("invalid_url") from err
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise PushieError("invalid_url")
    return value.strip().rstrip("/")


class PushieClient:
    def __init__(self, session, url, token):
        self.session, self.url, self.token = session, normalize_url(url), token

    async def request(self, method, path, payload=None, key=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        if key:
            headers["Idempotency-Key"] = key
        for attempt in range(3):
            delay = 1 + attempt
            try:
                async with self.session.request(
                    method,
                    self.url + path,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=False,
                ) as response:
                    status = response.status
                    if status == 200:
                        try:
                            result = await response.json()
                        except (ValueError, aiohttp.ContentTypeError) as err:
                            raise PushieError("unsupported_api") from err
                        if not isinstance(result, dict):
                            raise PushieError("unsupported_api")
                        return result
                    code = {
                        401: "invalid_auth",
                        403: "no_permission",
                        404: "not_found",
                        413: "too_large",
                        409: "conflict",
                        429: "rate_limited",
                    }.get(status, "server_error")
                    if status != 429 and status < 500:
                        raise PushieError(code, status)
                    retry = response.headers.get("Retry-After")
                    if retry:
                        try:
                            delay = max(0, float(retry))
                        except ValueError:
                            try:
                                delay = max(
                                    0,
                                    (
                                        parsedate_to_datetime(retry) - datetime.now(UTC)
                                    ).total_seconds(),
                                )
                            except (ValueError, TypeError):
                                delay = 2
                    if delay > 5 or attempt == 2:
                        raise PushieError(code, status)
            except (aiohttp.ClientError, TimeoutError) as err:
                if attempt == 2:
                    raise PushieError("cannot_connect") from err
            await asyncio.sleep(delay)
        raise PushieError("cannot_connect")

    async def verify(self):
        try:
            result = await self.request("POST", "/api/verify", {})
        except PushieError as err:
            if err.status == 404:
                raise PushieError("unsupported_api") from err
            raise
        if (
            result.get("ok") is not True
            or result.get("apiVersion") != 1
            or not {"topics:list", "topics:send", "verify"}.issubset(result.get("capabilities", []))
        ):
            raise PushieError("unsupported_api")

    async def topics(self):
        result = await self.request("GET", "/api/topics")
        topics = result.get("topics")
        if not isinstance(topics, list) or any(
            not isinstance(t, dict) or not isinstance(t.get("name"), str) for t in topics
        ):
            raise PushieError("unsupported_api")
        return {t["name"]: t.get("description", "") for t in topics}

    async def send(self, topic, message, title=None):
        title = "Home Assistant" if title is None else title
        if not message.strip() or len(message.encode()) > 2000 or len(title.encode()) > 160:
            raise PushieError("invalid_message")
        return await self.request(
            "POST",
            "/api/send",
            {
                "topic": topic,
                "title": title,
                "body": message,
            },
            key=uuid4().hex,
        )

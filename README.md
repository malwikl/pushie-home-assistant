# Pushie for Home Assistant

A UI-configured, topic-only notification integration for [Pushie](https://github.com/malwikl/pushie).

Copy `custom_components/pushie` into Home Assistant's `config/custom_components/` directory and restart Home Assistant. Add **Pushie** under Settings → Devices & services. Enter the server's HTTPS origin and an integration token, choose topics, then send an optional real test or skip it. The server must include `GET /api/topics` and `POST /api/verify` (API version 1). Older Pushie versions must be updated first. Create a key under Pushie → Administration → Integration keys. The server `SEND_TOKEN` also works. No administrator token is needed. Personal keys cannot pass topic verification. Integration keys work with both Home Assistant and Watchtower and may send to any destination through the API; the HA integration exposes topics only.

Use a selected topic in the visual automation editor with **Notifications: Send a notification message**, or YAML:

```yaml
action: notify.send_message
target:
  entity_id: notify.pushie_automation
data:
  title: Washing machine
  message: The washing machine has finished.
```

Entity IDs depend on your installation. Configure offers topic selection, explicit refresh, verification without sending, and real tests. The integration menu also supports URL reconfiguration and token reauthentication. Each test submission sends to all subscribers of exactly one selected topic. Results report inbox/queue counts, not confirmed receipt; zero inboxes means no subscribers, and inboxes with zero queued devices means inbox-only delivery.

Topics refresh every five minutes. Removed selected topics remain selected but unavailable; reappearing topics recover their existing identity. New topics require selection. Transient refresh failures retain the catalog. Entity IDs are backed by a persisted installation identity independent of URL and credentials.

Requests use TLS validation, bounded timeouts, no redirects, and up to three attempts for network failures, HTTP 429 and 5xx responses. Each logical send reuses one idempotency key across retries. Retry-After delays above five seconds are surfaced for a later manual retry. Outcomes can remain uncertain after a timeout or Home Assistant restart. Notification content is never silently truncated. Removing the integration does not delete notifications in Pushie.

Home Assistant reference: [notify entities](https://contributors.home-assistant.io/core/entities/notify/) and [configuration flows](https://contributors.home-assistant.io/core/integrations/config-flow/).

## Tests

The suite uses Home Assistant's official [`pytest-homeassistant`](https://github.com/home-assistant/core/tree/2026.11.1/packages/pytest-homeassistant) framework,
including a real `hass` instance, configuration-entry/flow managers, notify
services, entity registry, and HA's `aioclient_mock` HTTP fixture. Outgoing
Pushie calls are mocked; tests never send real notifications.

Use Python 3.14.2 or newer. `requirements-test.txt` pins Home Assistant and its
matching test framework to 2026.11.1; upgrade the two together. The framework
loads automatically, and custom integrations are enabled by its `hass` fixture.

```sh
python -m pip install -r requirements-test.txt
ruff check custom_components tests
ruff format --check custom_components tests
pytest --cov=custom_components.pushie --cov-report=term-missing
```

For a reproducible container environment:

```sh
docker build -f Dockerfile.test -t pushie-ha-tests .
docker run --rm pushie-ha-tests
```

GitHub Actions runs the same lint, formatting, and complete test suite and uploads
coverage. Tests cover authentication/retries and byte limits, setup/unload,
configuration/options flows, explicit test submissions, topic selection, HA's
`notify.send_message` service, and entity identity across topic disappearance.

# Pushie for Home Assistant

A UI-configured, topic-only notification integration for [Pushie](https://github.com/malwikl/pushie).

Copy `custom_components/pushie` into Home Assistant's `config/custom_components/` directory and restart Home Assistant. Add **Pushie** under Settings → Devices & services. Enter the server's HTTPS origin and `SEND_TOKEN`, choose topics, then send an optional real test or skip it. The server must include `GET /api/topics` and `POST /api/verify` (API version 1). Older Pushie versions must be updated first. No administrator token is needed. Personal and Watchtower keys cannot send to topics. The server-wide token has broader permissions than the topic-only UI exposes.

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

Requests use TLS validation, bounded timeouts, no redirects, and up to three attempts for network failures, HTTP 429 and 5xx responses. Each logical send reuses one idempotency key across retries. Retry-After delays above five seconds are surfaced for a later manual retry. Outcomes can remain uncertain after a timeout or Home Assistant restart. Message content is never silently truncated. Removing the integration does not delete messages in Pushie.

Development: install Home Assistant, pytest, pytest-asyncio, aioresponses and ruff; run `pytest -q` and `ruff check custom_components tests`. CI checks Python 3.13 with Home Assistant 2025.3.4 as the compatibility baseline. API client tests cover verification, byte limits, authentication failures, and retry deduplication. A live HA installation and receiving device are required to validate visual automations and actual delivery before release. This repository does not install or restart Home Assistant, or send live notifications during development.

Home Assistant reference: [notify entities](https://contributors.home-assistant.io/core/entities/notify/) and [configuration flows](https://contributors.home-assistant.io/core/integrations/config-flow/).

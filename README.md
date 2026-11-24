# Pushie for Home Assistant

A custom Home Assistant integration that sends [Pushie](https://github.com/malwikl/pushie) notifications from automations and scripts. Each selected Pushie topic becomes a Home Assistant `notify` entity.

## Install

### With HACS

If you already have HACS, use this badge to open Pushie as a custom repository. [Install HACS](https://www.hacs.xyz/docs/use/download/download/).

[![Open Pushie in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=malwikl&repository=pushie-home-assistant&category=integration)

1. If you prefer to add it from HACS, open **HACS → ⋮ → Custom repositories**, enter `https://github.com/malwikl/pushie-home-assistant`, select **Integration**, and choose **Add**. [HACS custom repository guide](https://www.hacs.xyz/docs/faq/custom_repositories/).
2. Open **Pushie** in HACS and select **Download**.
3. Restart Home Assistant and [set up Pushie](#set-up-pushie). Use HACS to download updates, then restart Home Assistant to apply them.

### Manual installation

1. [Download the ZIP](https://github.com/malwikl/pushie-home-assistant/archive/refs/heads/main.zip) and extract it.
2. Copy the `custom_components/pushie` folder into your Home Assistant configuration directory. The manifest should end up at `config/custom_components/pushie/manifest.json`. Create `custom_components` if needed. [Find your Home Assistant configuration directory](https://www.home-assistant.io/docs/configuration/).
3. Restart Home Assistant and [set up Pushie](#set-up-pushie).

To update a manual installation, replace the installed `custom_components/pushie` folder with the new copy and restart Home Assistant.

## Set up Pushie

1. Make sure Home Assistant can reach your Pushie server over HTTPS and that Pushie has at least one topic. The integration requires `GET /api/topics` and `POST /api/verify` (API version 1). [Pushie API documentation](https://github.com/malwikl/pushie/blob/main/docs/README.md#home-assistant-topic-api).
2. In Pushie, open **Administration → Integration keys**, create a key, and copy the token when it appears. The server `SEND_TOKEN` also works. Personal API keys lack topic access. Integration keys can send to any destination through the Pushie API.
3. After installing and restarting, use the badge below or go to **Settings → Devices & services → Add integration** and search for **Pushie**.
4. Enter the Pushie base URL (for example, `https://pushie.example.com`) and the integration token. Home Assistant verifies the connection, then lets you select the topics to use.
5. Choose **Skip / finish** to save or **Send test notification** to try a topic first. A test sends a real notification to the selected topic's subscribers. Finish setup to create the notify entities.

[![Add Pushie to My Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=pushie)

## Send a notification

Open **Settings → Tools → Actions**, choose **Send a notification message**, select your Pushie topic entity as the target, enter a message and optional title, and select **Perform action**. Use the same action in the automation or script editor. [Home Assistant action reference](https://www.home-assistant.io/actions/notify.send_message/).

[![Open the notification action in My Home Assistant](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=notify.send_message)

For YAML, replace `notify.pushie_automation` with the entity ID shown in your instance.

```yaml
action: notify.send_message
target:
  entity_id: notify.pushie_automation
data:
  title: Washing machine
  message: The washing machine has finished.
```

## Manage topics and credentials

Open **Settings → Devices & services → Pushie → Configure** to change topic selections, refresh the topic list, verify the connection without sending, or send another test notification. Use **Reconfigure** in the integration menu to update the URL or token. Home Assistant prompts for reauthentication if Pushie rejects the token.

[![Open Integrations in My Home Assistant](https://my.home-assistant.io/badges/integrations.svg)](https://my.home-assistant.io/redirect/integrations/)

Test results show how many inboxes received the notification and how many devices were queued for push. Zero inboxes means no subscribers. If the notification appears in an inbox with zero devices queued, check whether the topic is muted or whether push is enabled on a device subscribed to the topic.

Topics refresh every five minutes. Removed selected topics remain selected but unavailable; reappearing topics recover their existing identity. New topics require selection. Transient refresh failures retain the catalog. Entity IDs are backed by a persisted installation identity independent of URL and credentials.

Requests use TLS validation, bounded timeouts, no redirects, and up to three attempts for network failures, HTTP 429 and 5xx responses. Each logical send reuses one idempotency key across retries. Retry-After delays above five seconds are surfaced for a later manual retry. Outcomes can remain uncertain after a timeout or Home Assistant restart. Notification content is never silently truncated. Removing the integration does not delete notifications in Pushie.

See the Home Assistant developer documentation for [notify entities](https://contributors.home-assistant.io/core/entities/notify/) and [configuration flows](https://contributors.home-assistant.io/core/integrations/config-flow/).

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

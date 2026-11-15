"""One standard notify entity for each selected topic."""

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PushieError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        PushieNotify(entry.runtime_data, entry, topic) for topic in entry.options.get("topics", [])
    )


class PushieNotify(CoordinatorEntity, NotifyEntity):
    _attr_supported_features = NotifyEntityFeature.TITLE
    _attr_icon = "mdi:bell-outline"

    def __init__(self, coordinator, entry, topic):
        super().__init__(coordinator)
        self.topic, self.entry = topic, entry
        self._attr_unique_id = f"{entry.data['installation_id']}_{topic}"
        self._attr_name = f"Pushie {topic}"

    @property
    def available(self):
        return super().available and self.topic in (self.coordinator.data or {})

    async def async_send_message(self, message, title=None):
        try:
            await self.coordinator.client.send(self.topic, message, title)
        except PushieError as err:
            if err.code == "invalid_auth":
                self.entry.async_start_reauth(self.hass)
            if err.status == 404:
                await self.coordinator.async_request_refresh()
            raise HomeAssistantError(f"Pushie: {err.code}") from err

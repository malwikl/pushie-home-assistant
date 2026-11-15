"""Refresh the catalog without changing selected topics."""

import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PushieError


class PushieCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name="Pushie topics",
            config_entry=entry,
            update_interval=timedelta(minutes=5),
        )
        self.client = client

    async def _async_update_data(self):
        try:
            return await self.client.topics()
        except PushieError as err:
            if err.code == "invalid_auth":
                raise ConfigEntryAuthFailed("Invalid Pushie credentials") from err
            raise UpdateFailed(err.code) from err

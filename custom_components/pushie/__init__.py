"""Pushie topic notifications."""

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PushieClient, PushieError
from .coordinator import PushieCoordinator


async def async_setup_entry(hass, entry):
    client = PushieClient(async_get_clientsession(hass), entry.data["url"], entry.data["token"])
    try:
        await client.verify()
    except PushieError as err:
        if err.code == "invalid_auth":
            raise ConfigEntryAuthFailed(err.code) from err
        raise ConfigEntryNotReady(err.code) from err
    coordinator = PushieCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.NOTIFY])
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, [Platform.NOTIFY])

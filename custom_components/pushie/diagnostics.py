"""No credentials, URLs, recipients or message text in diagnostics."""


async def async_get_config_entry_diagnostics(hass, entry):
    return {
        "api_version": 1,
        "selected_topics": entry.options.get("topics", []),
        "catalog_refresh_ok": entry.runtime_data.last_update_success,
    }

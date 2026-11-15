"""UI setup, topic selection, verification and explicit real tests."""

from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PushieClient, PushieError
from .const import DOMAIN


class FlowMixin:
    def client(self):
        return PushieClient(
            async_get_clientsession(self.hass), self.credentials["url"], self.credentials["token"]
        )

    async def async_step_topics(self, user_input=None):
        errors = {}
        try:
            self.catalog = await self.client().topics()
            if user_input is not None:
                chosen = user_input["topics"]
                if chosen and set(chosen) <= (set(self.catalog) | set(self.selected)):
                    self.selected = chosen
                    return await self.async_step_test_choice()
                errors["base"] = "select_topics"
            if not self.catalog:
                errors["base"] = "no_topics"
        except PushieError as err:
            errors["base"] = err.code
        options = [
            {"value": name, "label": f"{name} — {self.catalog.get(name) or 'Unavailable'}"}
            for name in sorted(set(self.catalog) | set(self.selected))
        ]
        return self.async_show_form(
            step_id="topics",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("topics", default=self.selected): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options, multiple=True)
                    )
                }
            ),
        )

    async def async_step_test_choice(self, user_input=None):
        return self.async_show_menu(step_id="test_choice", menu_options=["test", "finish"])

    async def async_step_test(self, user_input=None):
        errors = {}
        defaults = user_input or {
            "topic": self.selected[0],
            "title": "Home Assistant",
            "message": "Pushie test notification",
        }
        if user_input is not None:
            try:
                if user_input["topic"] not in self.selected:
                    raise PushieError("select_topics")
                result = await self.client().send(
                    user_input["topic"], user_input["message"], user_input["title"]
                )
                self.feedback = f"Stored in {result.get('inboxUsers', 0)} inboxes; queued for {result.get('queued', 0)} devices. Receipt is unconfirmed."
                return await self.async_step_result()
            except PushieError as err:
                errors["base"] = err.code
        return self.async_show_form(
            step_id="test",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("topic", default=defaults["topic"]): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=self.selected)
                    ),
                    vol.Required("title", default=defaults["title"]): str,
                    vol.Required("message", default=defaults["message"]): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                }
            ),
        )

    async def async_step_result(self, user_input=None):
        if user_input is not None:
            return await self.async_step_finish()
        return self.async_show_form(
            step_id="result",
            data_schema=vol.Schema({}),
            description_placeholders={"result": self.feedback},
        )


class PushieConfigFlow(FlowMixin, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.credentials, self.catalog, self.selected = {}, {}, []
        self.edit_entry = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PushieOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.credentials = user_input
            try:
                client = self.client()
                await client.verify()
                self.credentials = {"url": client.url, "token": user_input["token"]}
                if self.edit_entry:
                    return self.async_update_reload_and_abort(
                        self.edit_entry, data_updates=self.credentials
                    )
                if any(e.data["url"] == client.url for e in self._async_current_entries()):
                    return self.async_abort(reason="already_configured")
                return await self.async_step_topics()
            except PushieError as err:
                errors["base"] = err.code
        defaults = user_input or self.credentials
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("url", default=defaults.get("url", "")): str,
                    vol.Required("token", default=defaults.get("token", "")): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
        )

    async def async_step_finish(self, user_input=None):
        return self.async_create_entry(
            title="Pushie",
            data={**self.credentials, "installation_id": uuid4().hex},
            options={"topics": self.selected},
        )

    async def async_step_reauth(self, entry_data):
        self.edit_entry = self._get_reauth_entry()
        self.credentials = dict(self.edit_entry.data)
        return await self.async_step_user()

    async def async_step_reconfigure(self, user_input=None):
        self.edit_entry = self._get_reconfigure_entry()
        self.credentials = dict(self.edit_entry.data)
        return await self.async_step_user()


class PushieOptionsFlow(FlowMixin, config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        self.credentials = dict(self.config_entry.data)
        self.selected = list(self.config_entry.options.get("topics", []))
        self.catalog = dict(self.config_entry.runtime_data.data or {})
        return self.async_show_menu(
            step_id="init", menu_options=["topics", "refresh", "verify", "test"]
        )

    async def async_step_refresh(self, user_input=None):
        await self.config_entry.runtime_data.async_request_refresh()
        return await self.async_step_topics()

    async def async_step_verify(self, user_input=None):
        try:
            await self.client().verify()
            self.feedback = "Connection verified. No notification was sent."
            return await self.async_step_result()
        except PushieError as err:
            return self.async_show_form(
                step_id="verify", data_schema=vol.Schema({}), errors={"base": err.code}
            )

    async def async_step_finish(self, user_input=None):
        return self.async_create_entry(title="", data={"topics": self.selected})

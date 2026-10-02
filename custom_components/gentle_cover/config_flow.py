"""Adding a room.

The curtains live in the entry's data, the movement settings in its options.
Curves are drawn rather than typed, so the settings are edited on the Gentle
Cover page; the Configure dialog only points there.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er, selector

from .const import CONF_COVERS, DOMAIN, MINOR_VERSION
from .options import defaults

COVERS_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="cover", multiple=True)
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
        vol.Required(CONF_COVERS): COVERS_SELECTOR,
    }
)


def _is_ours(hass: HomeAssistant, entity_id: str) -> bool:
    entry = er.async_get(hass).async_get(entity_id)
    return entry is not None and entry.platform == DOMAIN


class GentleCoverConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = MINOR_VERSION

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if any(_is_ours(self.hass, cover) for cover in user_input[CONF_COVERS]):
                # A gentle cover driving another one would plan steps on top
                # of steps, and the hands-off check would trip on itself.
                errors[CONF_COVERS] = "own_entity"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                    options=defaults(),
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GentleCoverOptionsFlow()


class GentleCoverOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Curves are drawn, not typed: the settings live on the page."""
        if user_input is not None:
            return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))

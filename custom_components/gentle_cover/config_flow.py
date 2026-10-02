"""Adding a room.

The curtains live in the entry's data, everything else in its options.
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

from .const import CONF_COVERS, DOMAIN, MINOR_VERSION, SET_POSITION_FEATURE
from .options import defaults, validate_covers, validate_title

COVERS_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="cover", multiple=True)
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
        vol.Required(CONF_COVERS): COVERS_SELECTOR,
    }
)


def describe_cover(hass: HomeAssistant, entity_id: str) -> str:
    """What a would-be member curtain is, for validate_covers."""
    entry = er.async_get(hass).async_get(entity_id)
    if entry is not None and entry.platform == DOMAIN:
        # A gentle cover driving another one would plan steps on top of
        # steps, and the hands-off check would trip on itself.
        return "ours"
    state = hass.states.get(entity_id)
    if state is None or not entity_id.startswith("cover."):
        return "missing"
    features = state.attributes.get("supported_features", 0)
    if not isinstance(features, int) or not features & SET_POSITION_FEATURE:
        return "no_position"
    return "ok"


def taken_titles(hass: HomeAssistant, except_entry_id: str | None = None) -> set[str]:
    return {
        entry.title
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != except_entry_id
    }


class GentleCoverConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = MINOR_VERSION

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                title = validate_title(user_input.get(CONF_NAME), taken_titles(self.hass))
            except ValueError:
                name = str(user_input.get(CONF_NAME) or "").strip()
                errors[CONF_NAME] = (
                    "no_name" if not name else "name_too_long" if len(name) > 64 else "name_taken"
                )
            covers = user_input.get(CONF_COVERS) or []
            if not covers:
                errors[CONF_COVERS] = "no_covers"
            else:
                for entity_id in covers:
                    kind = describe_cover(self.hass, entity_id)
                    if kind != "ok":
                        errors[CONF_COVERS] = {
                            "ours": "own_entity",
                            "missing": "missing_cover",
                            "no_position": "no_position",
                        }[kind]
                        break
            if not errors:
                covers = validate_covers(covers, lambda e: describe_cover(self.hass, e))
                return self.async_create_entry(
                    title=title,
                    data={CONF_NAME: title, CONF_COVERS: covers},
                    options=defaults(title, covers),
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

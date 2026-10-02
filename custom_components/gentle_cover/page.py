"""Serve the Gentle Cover page and card, and put the page in the sidebar.

Curves are drawn, and a settings dialog cannot draw: the page is where a
room's movement is edited. The card shows a room's curve on a dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

PAGE_COMPONENT = "gentle-cover-page"
PAGE_URL_PATH = "gentle-cover"
STATIC_URL = "/gentle_cover/frontend"

_VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
PAGE_MODULE_URL = f"{STATIC_URL}/gentle-cover-page.js?v={_VERSION}"
CARD_MODULE_URL = f"{STATIC_URL}/gentle-cover-card.js?v={_VERSION}"


async def async_setup_page(hass: HomeAssistant) -> None:
    static_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(static_dir), True)]
    )
    # The version in the URL makes browsers fetch a changed file after an
    # update instead of the cached one.
    frontend.add_extra_js_url(hass, PAGE_MODULE_URL)
    frontend.add_extra_js_url(hass, CARD_MODULE_URL)
    frontend.async_register_built_in_panel(
        hass,
        PAGE_COMPONENT,
        sidebar_title="Gentle Cover",
        sidebar_icon="mdi:curtains",
        frontend_url_path=PAGE_URL_PATH,
        require_admin=True,
    )

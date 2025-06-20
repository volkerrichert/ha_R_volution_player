import logging
from typing import Any, TypedDict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)

class RVolutionPlayerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    def __init__(self) -> None:
        """Initialize config flow."""
        self._entry: config_entries.ConfigEntry | None = None
        self._host: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self._show_setup_form_init(errors)

        self._host = user_input[CONF_HOST]

        if error := await self.validate_input():
            return self._show_setup_form_init({"base": error})

        # await self.async_set_unique_id(
        #     f"{self._proxy.e3dc.serialNumberPrefix}{self._proxy.e3dc.serialNumber}"
        # )
        self._abort_if_unique_id_configured()
        final_data: dict[str, Any] = user_input

        return self.async_create_entry(
            title=f"R_volution", data=final_data
        )

    def _show_setup_form_init(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors or {},
        )

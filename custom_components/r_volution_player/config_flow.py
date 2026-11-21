"""Config flow for the R_volution Player integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import (
    ATTR_MODEL,
    ATTR_MODEL_ID,
    ATTR_SERIAL_NUMBER,
    CONF_API_KEY,
    CONF_EMAIL,
    CONF_HOST,
    CONF_PASSWORD,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import RVolutionCollectionClient, RVolutionPlayerClient
from .const import CREDENTIAL_KEYS, DOMAIN, ERROR_CANNOT_CONNECT, IR_CODES

_LOGGER = logging.getLogger(__name__)

HOST_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Optional(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
        vol.Optional(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="off")
        ),
    }
)


async def _async_get_player_status(host: str) -> dict[str, Any] | None:
    """Return the player's status, or None if it cannot be reached."""
    api = RVolutionPlayerClient(host)
    try:
        return await api.async_update_status() or None
    except Exception:
        _LOGGER.exception("Error connecting to R_volution player at %s", host)
        return None
    finally:
        await api.close()


def _unique_id(status: dict[str, Any]) -> str:
    """Build the config entry unique id from the player's status."""
    return f"{status.get('product_id')}-{status['serial_number']}"


class RVolutionPlayerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for the R_volution Player integration.

    Only the player's host is configured here; the optional collection
    credentials live in the options flow.
    """

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            if (status := await _async_get_player_status(host)) is None:
                errors["base"] = ERROR_CANNOT_CONNECT
            else:
                await self.async_set_unique_id(_unique_id(status))
                self._abort_if_unique_id_configured()

                await RVolutionPlayerClient(host)._send_ip_command(IR_CODES["home"])

                return self.async_create_entry(
                    title=status["product_name"],
                    data={
                        CONF_HOST: host,
                        ATTR_MODEL: status["product_name"],
                        ATTR_SERIAL_NUMBER: status["serial_number"],
                        ATTR_MODEL_ID: status.get("product_id"),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(HOST_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the host of an existing player."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            if (status := await _async_get_player_status(host)) is None:
                errors["base"] = ERROR_CANNOT_CONNECT
            else:
                await self.async_set_unique_id(_unique_id(status))
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_HOST: host}
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                HOST_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        """Return the options flow handler for this integration."""
        return RVolutionOptionsFlowHandler()


async def _async_validate_credentials(data: dict[str, Any]) -> str | None:
    """Log in to the R_volution collection; return an error key on failure."""
    client = RVolutionCollectionClient(
        data[CONF_EMAIL], data[CONF_PASSWORD], data[CONF_API_KEY]
    )
    try:
        if await client.async_auth() is None:
            return "invalid_auth"
    except Exception:
        _LOGGER.exception("Error connecting to the R_volution collection")
        return ERROR_CANNOT_CONNECT
    finally:
        await client.close()
    return None


class RVolutionOptionsFlowHandler(OptionsFlowWithReload):
    """Collection credentials for R_volution Player."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the collection credentials (all three or none)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            credentials = {k: user_input[k] for k in CREDENTIAL_KEYS if user_input.get(k)}
            if credentials and len(credentials) != len(CREDENTIAL_KEYS):
                errors["base"] = "incomplete_credentials"
            elif credentials and (error := await _async_validate_credentials(credentials)):
                errors["base"] = error
            else:
                return self.async_create_entry(data=credentials)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, user_input or self.config_entry.options
            ),
            errors=errors,
        )

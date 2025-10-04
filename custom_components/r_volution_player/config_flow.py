"""Constants for the E3DC Remote Storage Control Protocol integration."""

import logging
from typing import Any

from httpcore import TimeoutException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_API_KEY,
    ATTR_MODEL,
    ATTR_MODEL_ID,
    ATTR_SERIAL_NUMBER,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError, ConfigEntryNotReady

from custom_components.r_volution_player.api import (
    RVolutionCollectionClient,
    RVolutionPlayerClient,
)

from .const import DOMAIN, ERROR_CANNOT_CONNECT, IR_CODES

_LOGGER = logging.getLogger(__name__)


class RVolutionPlayerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the RVolution Player integration.

    This class handles the setup and validation of user input for configuring
    the RVolution Player integration in Home Assistant.
    """

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._entry: config_entries.ConfigEntry | None = None
        self._api: RVolutionPlayerClient | None = None

    async def _async_validate_input(self, user_input: dict[str, Any]) -> str | None:
        """Validate the user input by connecting to the RVolutionPlayer API."""

        try:
            _host = user_input[CONF_HOST]
            _email = user_input[CONF_EMAIL]
            _password = user_input[CONF_PASSWORD]
            _apiKey = user_input[CONF_API_KEY]

            assert isinstance(_host, str)
            self._api = RVolutionPlayerClient(_host)
            _collection_client = (
                await RVolutionCollectionClient(_email, _password, _apiKey).async_auth()
                if _email and _password and _apiKey
                else None
            )

            await self._api.async_update_status()
        except (TimeoutError, HomeAssistantError, TimeoutException) as ex:
            raise ConfigEntryNotReady(f"Timeout while connecting to {_host}") from ex

        except Exception as e:
            _LOGGER.error("Error connecting to RVolutionPlayer: %s", e)
            return ERROR_CANNOT_CONNECT
        finally:
            await self._api.close()
            _collection_client.close() if _collection_client else None
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self._show_setup_form_init(errors)

        self._host = user_input[CONF_HOST]

        if error := await self._async_validate_input(user_input):
            return self._show_setup_form_init({"base": error})

        await self._api._send_ip_command(IR_CODES["home"])
        product_name = await self._api.async_product_name()
        product_id = await self._api.async_get_product_id()
        serial_number = await self._api.async_get_serial_number()

        await self.async_set_unique_id(f"{product_id}-{serial_number}")
        self._abort_if_unique_id_configured()

        final_data: dict[str, Any] = user_input
        final_data[ATTR_MODEL] = product_name
        final_data[ATTR_SERIAL_NUMBER] = serial_number
        final_data[ATTR_MODEL_ID] = product_id

        return self.async_create_entry(
            title=f"{await self._api.async_product_name()}",
            description=f"{self._host}",
            data=final_data,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle reconfiguration of the integration."""
        if user_input is not None:
            self._host = user_input[CONF_HOST]

            if error := await self._async_validate_input(user_input):
                return self._show_setup_form_init({"base": error})

            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._create_user_data_schema(
                self._get_reconfigure_entry().data
            ),
            errors={},
            description_placeholders={},
        )

    def _show_setup_form_init(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=self._create_user_data_schema(),
            errors=errors or {},
        )

    def _create_user_data_schema(
        self, data: dict[str, Any] | None = None
    ) -> vol.Schema:
        """Create the user data schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=data.get(CONF_HOST, vol.UNDEFINED)
                ): str,
                vol.Optional(
                    CONF_EMAIL, default=data.get(CONF_EMAIL, vol.UNDEFINED)
                ): str,
                vol.Optional(
                    CONF_PASSWORD, default=data.get(CONF_PASSWORD, vol.UNDEFINED)
                ): str,
                vol.Optional(
                    CONF_API_KEY, default=data.get(CONF_API_KEY, vol.UNDEFINED)
                ): str,
            }
        )

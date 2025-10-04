"""Coordinator for R_volution Player integration.

This module defines the RVolutionCoordinator class, which manages data updates and service calls
for the R_volution Player integration in Home Assistant.
"""

from datetime import timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import (CONF_HOST, CONF_EMAIL, CONF_PASSWORD, CONF_API_KEY, ATTR_MODEL,ATTR_MODEL_ID, ATTR_SERIAL_NUMBER)

from custom_components.r_volution_player.const import DOMAIN
from .api import RVideoClient, RVolutionPlayerClient, RVolutionCollectionClient
import logging

_LOGGER = logging.getLogger(__name__)

class RVolutionCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """RVolution Coordinator, fetches all relevant data and provides proxies for all service calls."""

    _attr_device_info: DeviceInfo | None = None
    media_info: dict[str, Any] = {}

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize E3DC Coordinator and connect."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
            config_entry=config_entry,
        )

        assert isinstance(config_entry.unique_id, str)
        self.uid: str = config_entry.unique_id
        self.host = config_entry.data.get(CONF_HOST, None)
        self._model = config_entry.data.get(ATTR_MODEL)
        self._model_id = config_entry.data.get(ATTR_MODEL_ID)
        self._serial_number = config_entry.data.get(ATTR_SERIAL_NUMBER)

        assert self.host, "Host must be provided in the configuration entry."

        self._apiKey = config_entry.data.get(CONF_API_KEY, None)
        self._email = config_entry.data.get(CONF_EMAIL, None)
        self._password = config_entry.data.get(CONF_PASSWORD, None)
        self._attr_device_info = None

        self.api = RVolutionPlayerClient(self.host)
        self.collection_client = RVolutionCollectionClient(self._email, self._password, self._apiKey) if self._email and self._password and self._apiKey else None
        self.rvideo_client = RVideoClient(self.host)

        self.media_info: dict[str, Any] = {}

    async def _async_setup(self) -> None:
        if self.collection_client:
            await self.collection_client.async_auth()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the R_volution Player API."""
        try:
            current_url = self.data.get("playback_url", None) if self.data else None

            data = await self.api.async_update_status()

            if (data.get("player_state", None) == "file_playback"):
                if current_url != data.get("playback_url", None):
                    self.media_info = await self.rvideo_client.async_get_media_info()
            else:
                self.media_info = {}

            if self._attr_device_info is None:
                self._attr_device_info = DeviceInfo(
                    manufacturer="R_volution",
                    model=f"{self._model} ({self._model_id})",
                    name=data.get("product_name", "R_volution Player"),
                    serial_number=self._serial_number,
                    identifiers={(DOMAIN, self.uid)},
                    sw_version=data.get("firmware_version", "Unknown")
                )
            return data
        except Exception as err:
            _LOGGER.error("Error fetching player data: %s", err)
            raise UpdateFailed(f"Error fetching player data: {err}")

    @property
    def device_info(self) -> DeviceInfo:
        """Return default device info structure."""
        return self._attr_device_info


    @property
    def apiKey(self) -> str:
        """Return the API key."""
        return self._apiKey

    @property
    def authKey(self) -> str:
        """Return the authentication key."""
        return self.collection_client.authKey if self.collection_client else None

    @property
    def email(self) -> str:
        """Return the email used for authentication."""
        return self._email if self._email else None

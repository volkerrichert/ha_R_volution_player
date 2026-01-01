"""Remote platform for R_volution Player integration."""

from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import RemoteEntity, RemoteEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, IR_CODES
from .coordinator import RVolutionCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the R_volution Player remote platform."""

    assert isinstance(config_entry.unique_id, str)
    coordinator: RVolutionCoordinator = hass.data[DOMAIN][config_entry.unique_id]
    remote = RVolutionPlayerRemote(
        coordinator,
        RVolutionPlayerRemoteDescription(
            key="remote",
            translation_key="system-media_player-percent",
            icon="mdi:remote",
        ),
        config_entry.entry_id,
    )
    async_add_entities([remote], True)


class RVolutionPlayerRemoteDescription(RemoteEntityDescription):
    """Class describing R_volution Player remote entities."""


class RVolutionPlayerRemote(CoordinatorEntity, RemoteEntity):
    """Representation of a R_volution Player remote."""

    def __init__(
        self,
        coordinator: RVolutionCoordinator,
        description: RemoteEntityDescription,
        entry_id: str,
        device_info: DeviceInfo | None = None,
    ):
        """Initialize the remote."""
        super().__init__(coordinator)
        self._attr_device_info = device_info
        self._attr_should_poll = False

        self._attr_is_on = False
        self.coordinator = coordinator
        self.entity_description: RVolutionPlayerRemoteDescription = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

        self.host = coordinator.host

        self._attr_name = f"{self.coordinator._model} ({self.host})"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_is_on = (
            self.coordinator.data.get("protocol_version", None) is not None
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the remote off."""
        await self.async_send_command([IR_CODES.power_off])
        self.async_write_ha_state()

    async def async_send_command(self, commands: Iterable[str], **kwargs: Any) -> None:
        """Send commands to a device."""
        if not self._is_on:
            return

        # Here you would implement the logic to send the command to the R_volution Player.
        # For example, using the coordinator's API client.
        for command in commands:
            await self.coordinator.api.async_send_command(command)

        # Optionally, refresh the state after sending the command
        await self.coordinator.async_request_refresh()

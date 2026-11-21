"""Remote platform for R_volution Player integration."""

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    DEFAULT_NUM_REPEATS,
    RemoteEntity,
    RemoteEntityDescription,
)
from homeassistant.config_entries import ConfigEntryError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RVolutionCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the R_volution Player remote platform."""

    if not isinstance(config_entry.unique_id, str):
        raise ConfigEntryError("Invalid unique_id in config entry")
    coordinator: RVolutionCoordinator = hass.data[DOMAIN][config_entry.unique_id]
    remote = RVolutionPlayerRemote(
        coordinator,
        RemoteEntityDescription(key="remote", icon="mdi:remote"),
        config_entry.entry_id,
    )
    async_add_entities([remote])


class RVolutionPlayerRemote(CoordinatorEntity[RVolutionCoordinator], RemoteEntity):
    """Representation of a R_volution Player remote.

    Commands are names from IR_CODES (e.g. "up", "enter", "home"); unknown
    values are sent as raw IR codes.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RVolutionCoordinator,
        description: RemoteEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the remote."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_name = f"{coordinator._model} ({coordinator.host})"

    @property
    def is_on(self) -> bool:
        """Return True if the player answers status requests."""
        data = self.coordinator.data or {}
        return data.get("protocol_version") is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the player on."""
        await self.async_send_command(["power_on"])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the player off."""
        await self.async_send_command(["power_off"])

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send IR commands to the player."""
        num_repeats = kwargs.get(ATTR_NUM_REPEATS, DEFAULT_NUM_REPEATS)
        delay_secs = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)

        first = True
        for _ in range(num_repeats):
            for cmd in command:
                if not first:
                    await asyncio.sleep(delay_secs)
                first = False
                await self.coordinator.api._send_ip_command(cmd)

        await self.coordinator.async_request_refresh()

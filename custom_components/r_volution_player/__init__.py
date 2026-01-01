"""Initialisierung der Integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import RVolutionCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the R_volution Player integration from a config entry."""

    assert isinstance(config_entry.unique_id, str)
    coordinator: RVolutionCoordinator = RVolutionCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.unique_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_ok

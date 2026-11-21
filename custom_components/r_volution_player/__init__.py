"""Initialisierung der Integration."""

from homeassistant.config_entries import ConfigEntry, ConfigEntryError
from homeassistant.core import HomeAssistant

from .const import CREDENTIAL_KEYS, DOMAIN, PLATFORMS
from .coordinator import RVolutionCoordinator


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if config_entry.version > 1:
        return False

    if config_entry.minor_version < 2:
        # 1.2: collection credentials moved from data to options.
        data = dict(config_entry.data)
        options = dict(config_entry.options)
        for key in CREDENTIAL_KEYS:
            if value := data.pop(key, None):
                options[key] = value
        hass.config_entries.async_update_entry(
            config_entry, data=data, options=options, minor_version=2
        )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the R_volution Player integration from a config entry."""

    if not isinstance(config_entry.unique_id, str):
        raise ConfigEntryError("Invalid unique_id in config entry")
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

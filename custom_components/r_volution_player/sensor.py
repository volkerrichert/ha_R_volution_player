"""R_volution player sensor platform."""
import logging
from dataclasses import dataclass
from typing import Any, Final


from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
)
from .coordinator import RVolutionCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class RVolutionSensorEntityDescription(SensorEntityDescription):
    """Class describing RVolution Sensor entities."""

SENSOR_DESCRIPTIONS: Final[tuple[RVolutionSensorEntityDescription, ...]] = (
    # DIAGNOSTIC SENSORS
    RVolutionSensorEntityDescription(
        key="Title",
        translation_key="media-info-title",
        icon="mdi:text-box",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    RVolutionSensorEntityDescription(
        key="Synopsis",
        translation_key="media-info-synopsis",
        icon="mdi:text-box",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Initialize Sensor Platform."""
    assert isinstance(entry.unique_id, str)
    coordinator: RVolutionCoordinator = hass.data[DOMAIN][entry.unique_id]
    entities: list[RVolutionPlayerSensor] = [
        RVolutionPlayerSensor(coordinator, description, entry.unique_id)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)

class RVolutionPlayerSensor(CoordinatorEntity, SensorEntity):
    """Custom E3DC Sensor implementation."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RVolutionCoordinator,
        description: RVolutionSensorEntityDescription,
        uid: str,
        device_info: DeviceInfo | None = None
    ) -> None:
        """Initialize the Sensor."""
        super().__init__(coordinator)
        self.coordinator: RVolutionCoordinator = coordinator
        self.entity_description: RVolutionSensorEntityDescription = description
        self._attr_unique_id = f"{uid}_{description.key}"

        if device_info is not None:
            self._deviceInfo = device_info
        else:
            self._deviceInfo = self.coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return the reported sensor value."""
        value = self.coordinator.media_info.get(self.entity_description.key)
        # Truncate state to 255 characters to comply with Home Assistant limits
        if value and isinstance(value, str) and len(value) > 255:
            return value[:252] + "..."
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        value = self.coordinator.media_info.get(self.entity_description.key)
        # Store full value in attributes if it exceeds state limit
        if value and isinstance(value, str) and len(value) > 255:
            return {
                "full_text": value,
                "truncated": True,
            }
        return {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return self._deviceInfo

    def get_icon(self) -> str | None:
        """Return the icon for the sensor."""
        value: str = self.coordinator.data.get(self.entity_description.key)
        if self.entity_description.icon is not None:
            return self.entity_description.icon

        return None

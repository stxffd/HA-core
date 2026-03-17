"""Binary sensor platform for BMW CarData integration.

Creates binary sensors for doors, locks, windows, trunk, hood, etc.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BMWCarDataConfigEntry
from .const import BINARY_DESCRIPTORS, DOMAIN
from .coordinator import BMWCarDataCoordinator

_LOGGER = logging.getLogger(__name__)


BINARY_SENSOR_DESCRIPTIONS: dict[str, BinarySensorEntityDescription] = {
    # Doors (isOpen)
    "vehicle.cabin.door.row1.driver.isOpen": BinarySensorEntityDescription(
        key="door_driver",
        translation_key="door_driver",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    "vehicle.cabin.door.row1.passenger.isOpen": BinarySensorEntityDescription(
        key="door_passenger",
        translation_key="door_passenger",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    "vehicle.cabin.door.row2.driver.isOpen": BinarySensorEntityDescription(
        key="door_rear_driver",
        translation_key="door_rear_driver",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    "vehicle.cabin.door.row2.passenger.isOpen": BinarySensorEntityDescription(
        key="door_rear_passenger",
        translation_key="door_rear_passenger",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    # Locks (isLocked)
    "vehicle.cabin.door.row1.driver.isLocked": BinarySensorEntityDescription(
        key="lock_driver",
        translation_key="lock_driver",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    "vehicle.cabin.door.row1.passenger.isLocked": BinarySensorEntityDescription(
        key="lock_passenger",
        translation_key="lock_passenger",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    "vehicle.cabin.door.row2.driver.isLocked": BinarySensorEntityDescription(
        key="lock_rear_driver",
        translation_key="lock_rear_driver",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    "vehicle.cabin.door.row2.passenger.isLocked": BinarySensorEntityDescription(
        key="lock_rear_passenger",
        translation_key="lock_rear_passenger",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    # Windows (isOpen)
    "vehicle.cabin.door.row1.driver.window.isOpen": BinarySensorEntityDescription(
        key="window_driver",
        translation_key="window_driver",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    "vehicle.cabin.door.row1.passenger.window.isOpen": BinarySensorEntityDescription(
        key="window_passenger",
        translation_key="window_passenger",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    "vehicle.cabin.door.row2.driver.window.isOpen": BinarySensorEntityDescription(
        key="window_rear_driver",
        translation_key="window_rear_driver",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    "vehicle.cabin.door.row2.passenger.window.isOpen": BinarySensorEntityDescription(
        key="window_rear_passenger",
        translation_key="window_rear_passenger",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    # Trunk and hood
    "vehicle.body.trunk.isOpen": BinarySensorEntityDescription(
        key="trunk",
        translation_key="trunk",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car-back",
    ),
    "vehicle.body.hood.isOpen": BinarySensorEntityDescription(
        key="hood",
        translation_key="hood",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car",
    ),
    # Motion
    "vehicle.body.isMoving": BinarySensorEntityDescription(
        key="is_moving",
        translation_key="is_moving",
        device_class=BinarySensorDeviceClass.MOVING,
    ),
    # Parking brake
    "vehicle.cabin.parkingBrake.isActive": BinarySensorEntityDescription(
        key="parking_brake",
        translation_key="parking_brake",
        icon="mdi:car-brake-parking",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BMWCarDataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BMW CarData binary sensors."""
    coordinator: BMWCarDataCoordinator = entry.runtime_data

    entities: list[BMWCarDataBinarySensor] = []

    if coordinator.data:
        for vin, vehicle_data in coordinator.data.vehicles.items():
            for descriptor_name in vehicle_data.telematic_data:
                if descriptor_name not in BINARY_DESCRIPTORS:
                    continue

                description = BINARY_SENSOR_DESCRIPTIONS.get(descriptor_name)
                if description is None:
                    continue

                entities.append(
                    BMWCarDataBinarySensor(
                        coordinator=coordinator,
                        vin=vin,
                        descriptor_name=descriptor_name,
                        description=description,
                    )
                )

    async_add_entities(entities)


class BMWCarDataBinarySensor(
    CoordinatorEntity[BMWCarDataCoordinator], BinarySensorEntity
):
    """Binary sensor entity for BMW CarData."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BMWCarDataCoordinator,
        vin: str,
        descriptor_name: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._descriptor_name = descriptor_name
        self._attr_unique_id = f"{vin}_{description.key}"

        vehicle = self._get_vehicle()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=f"BMW {vehicle.model_name}" if vehicle else f"BMW ({vin[-6:]})",
            manufacturer="BMW",
            model=vehicle.model_name if vehicle else None,
        )

    def _get_vehicle(self) -> Any:
        """Get the vehicle object."""
        if self.coordinator.data and self._vin in self.coordinator.data.vehicles:
            return self.coordinator.data.vehicles[self._vin].vehicle
        return None

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        vehicle_data = self.coordinator.data.vehicles.get(self._vin)
        if not vehicle_data:
            return None

        entry = vehicle_data.telematic_data.get(self._descriptor_name)
        if entry is None:
            return None

        value = entry.value.lower()

        # For locks, "isLocked" means on=locked, but BinarySensorDeviceClass.LOCK
        # interprets on=unlocked. So we need to invert for locks.
        if self.device_class == BinarySensorDeviceClass.LOCK:
            return value not in ("true", "1", "yes", "locked")

        return value in ("true", "1", "yes", "open", "active")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        if not self.coordinator.data:
            return None

        vehicle_data = self.coordinator.data.vehicles.get(self._vin)
        if not vehicle_data:
            return None

        entry = vehicle_data.telematic_data.get(self._descriptor_name)
        if entry is None:
            return None

        return {
            "descriptor": self._descriptor_name,
            "timestamp": entry.timestamp,
            "raw_value": entry.value,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

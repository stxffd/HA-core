"""Device tracker platform for BMW CarData integration.

Creates a device tracker entity using GPS coordinates from telematics data.
"""

from __future__ import annotations

from contextlib import suppress
import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BMWCarDataConfigEntry
from .const import DOMAIN
from .coordinator import BMWCarDataCoordinator

_LOGGER = logging.getLogger(__name__)

LAT_DESCRIPTOR = "vehicle.cabin.infotainment.navigation.currentLocation.latitude"
LON_DESCRIPTOR = "vehicle.cabin.infotainment.navigation.currentLocation.longitude"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BMWCarDataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BMW CarData device tracker."""
    coordinator: BMWCarDataCoordinator = entry.runtime_data

    entities: list[BMWCarDataDeviceTracker] = []

    if coordinator.data:
        for vin, vehicle_data in coordinator.data.vehicles.items():
            # Only create tracker if we have location data
            has_lat = LAT_DESCRIPTOR in vehicle_data.telematic_data
            has_lon = LON_DESCRIPTOR in vehicle_data.telematic_data
            if has_lat or has_lon:
                entities.append(
                    BMWCarDataDeviceTracker(
                        coordinator=coordinator,
                        vin=vin,
                    )
                )

    async_add_entities(entities)


class BMWCarDataDeviceTracker(CoordinatorEntity[BMWCarDataCoordinator], TrackerEntity):
    """Device tracker entity for BMW CarData vehicle location."""

    _attr_has_entity_name = True
    _attr_translation_key = "location"
    _attr_icon = "mdi:car"

    def __init__(
        self,
        coordinator: BMWCarDataCoordinator,
        vin: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._vin = vin
        self._attr_unique_id = f"{vin}_location"

        vehicle = self._get_vehicle()
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=f"BMW {vehicle.model_name}" if vehicle else f"BMW ({vin[-6:]})",
            manufacturer="BMW",
            model=vehicle.model_name if vehicle else None,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this tracker."""
        return self._device_info

    def _get_vehicle(self) -> Any:
        """Get the vehicle object."""
        if self.coordinator.data and self._vin in self.coordinator.data.vehicles:
            return self.coordinator.data.vehicles[self._vin].vehicle
        return None

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self._get_coordinate(LAT_DESCRIPTOR)

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self._get_coordinate(LON_DESCRIPTOR)

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device tracker."""
        return SourceType.GPS

    def _get_coordinate(self, descriptor: str) -> float | None:
        """Get a coordinate value from telematics data."""
        if not self.coordinator.data:
            return None

        vehicle_data = self.coordinator.data.vehicles.get(self._vin)
        if not vehicle_data:
            return None

        entry = vehicle_data.telematic_data.get(descriptor)
        if entry is None:
            return None

        try:
            return float(entry.value)
        except ValueError, TypeError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        attrs: dict[str, Any] = {}

        if not self.coordinator.data:
            return attrs

        vehicle_data = self.coordinator.data.vehicles.get(self._vin)
        if not vehicle_data:
            return attrs

        # Add heading if available
        heading_entry = vehicle_data.telematic_data.get(
            "vehicle.cabin.infotainment.navigation.currentLocation.heading"
        )
        if heading_entry:
            with suppress(ValueError, TypeError):
                attrs["heading"] = float(heading_entry.value)

        # Add speed if available
        speed_entry = vehicle_data.telematic_data.get(
            "vehicle.cabin.infotainment.navigation.currentLocation.speed"
        )
        if speed_entry:
            with suppress(ValueError, TypeError):
                attrs["speed"] = float(speed_entry.value)

        # Add timestamp from lat entry
        lat_entry = vehicle_data.telematic_data.get(LAT_DESCRIPTOR)
        if lat_entry:
            attrs["gps_timestamp"] = lat_entry.timestamp

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

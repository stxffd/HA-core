"""Sensor platform for BMW CarData integration.

Creates sensors from telematics data such as mileage, fuel level,
battery state of charge, charging power, tyre pressure, etc.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BMWCarDataConfigEntry
from .const import BINARY_DESCRIPTORS, DOMAIN, LOCATION_DESCRIPTORS
from .coordinator import BMWCarDataCoordinator

_LOGGER = logging.getLogger(__name__)


# Mapping from descriptor path to sensor entity description
SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "vehicle.chassis.mileage": SensorEntityDescription(
        key="mileage",
        translation_key="mileage",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
    ),
    "vehicle.powertrain.combustionEngine.remainingFuelLiters": SensorEntityDescription(
        key="fuel_level",
        translation_key="fuel_level",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-station",
    ),
    "vehicle.powertrain.combustionEngine.remainingFuelPercent": SensorEntityDescription(
        key="fuel_level_percent",
        translation_key="fuel_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-station",
    ),
    "vehicle.powertrain.combustionEngine.remainingRange": SensorEntityDescription(
        key="fuel_range",
        translation_key="fuel_range",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-station-outline",
    ),
    "vehicle.powertrain.combustionEngine.combinedFuelConsumption": SensorEntityDescription(
        key="fuel_consumption",
        translation_key="fuel_consumption",
        native_unit_of_measurement="L/100km",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fuel",
    ),
    "vehicle.powertrain.electric.battery.stateOfCharge": SensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "vehicle.powertrain.electric.battery.remainingRange": SensorEntityDescription(
        key="battery_range",
        translation_key="battery_range",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:ev-station",
    ),
    "vehicle.powertrain.electric.battery.charging.power": SensorEntityDescription(
        key="charging_power",
        translation_key="charging_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "vehicle.powertrain.electric.battery.charging.status": SensorEntityDescription(
        key="charging_status",
        translation_key="charging_status",
        icon="mdi:battery-charging",
    ),
    "vehicle.powertrain.electric.battery.charging.chargingTarget": SensorEntityDescription(
        key="charging_target",
        translation_key="charging_target",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-charging-100",
    ),
    "vehicle.cabin.hvac.ambientAirTemperature": SensorEntityDescription(
        key="ambient_temperature",
        translation_key="ambient_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "vehicle.chassis.axle.row1.wheel.left.tire.pressure": SensorEntityDescription(
        key="tyre_pressure_fl",
        translation_key="tyre_pressure_fl",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    "vehicle.chassis.axle.row1.wheel.right.tire.pressure": SensorEntityDescription(
        key="tyre_pressure_fr",
        translation_key="tyre_pressure_fr",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    "vehicle.chassis.axle.row2.wheel.left.tire.pressure": SensorEntityDescription(
        key="tyre_pressure_rl",
        translation_key="tyre_pressure_rl",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    "vehicle.chassis.axle.row2.wheel.right.tire.pressure": SensorEntityDescription(
        key="tyre_pressure_rr",
        translation_key="tyre_pressure_rr",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    "vehicle.cabin.infotainment.navigation.currentLocation.speed": SensorEntityDescription(
        key="speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
    "vehicle.cabin.infotainment.navigation.currentLocation.heading": SensorEntityDescription(
        key="heading",
        native_unit_of_measurement="°",
        icon="mdi:compass",
    ),
    # Battery management / electric engine
    "vehicle.drivetrain.batteryManagement.header": SensorEntityDescription(
        key="battery_management",
        translation_key="battery_management",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "vehicle.drivetrain.batteryManagement.maxEnergy": SensorEntityDescription(
        key="battery_max_energy",
        translation_key="battery_max_energy",
        native_unit_of_measurement="kWh",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-high",
    ),
    "vehicle.drivetrain.electricEngine.charging.status": SensorEntityDescription(
        key="electric_charging_status",
        translation_key="electric_charging_status",
        icon="mdi:ev-plug-type2",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BMWCarDataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BMW CarData sensors from a config entry."""
    coordinator: BMWCarDataCoordinator = entry.runtime_data

    entities: list[BMWCarDataSensor] = []

    if coordinator.data:
        for vin, vehicle_data in coordinator.data.vehicles.items():
            for descriptor_name, telematic_entry in vehicle_data.telematic_data.items():
                # Skip binary and location descriptors (handled by other platforms)
                if descriptor_name in BINARY_DESCRIPTORS:
                    continue
                if descriptor_name in LOCATION_DESCRIPTORS:
                    continue

                description = SENSOR_DESCRIPTIONS.get(descriptor_name)
                if description is None:
                    # Create a generic sensor for unknown descriptors
                    key = descriptor_name.split(".")[-1]
                    description = SensorEntityDescription(
                        key=key,
                        name=_format_descriptor_name(descriptor_name),
                        state_class=SensorStateClass.MEASUREMENT
                        if _is_numeric(telematic_entry.value)
                        else None,
                        native_unit_of_measurement=telematic_entry.unit or None,
                    )

                entities.append(
                    BMWCarDataSensor(
                        coordinator=coordinator,
                        vin=vin,
                        descriptor_name=descriptor_name,
                        description=description,
                    )
                )

    async_add_entities(entities)


def _format_descriptor_name(descriptor: str) -> str:
    """Convert a descriptor path to a human-readable name.

    Example: vehicle.cabin.door.row1.driver.isOpen -> Cabin Door Row1 Driver Is Open
    """
    parts = descriptor.replace("vehicle.", "").split(".")
    words: list[str] = []
    for part in parts:
        # Split camelCase
        result: list[str] = []
        current: list[str] = []
        for char in part:
            if char.isupper() and current:
                result.append("".join(current))
                current = [char]
            else:
                current.append(char)
        if current:
            result.append("".join(current))
        words.extend(w.capitalize() for w in result)
    return " ".join(words)


def _is_numeric(value: str) -> bool:
    """Check if a string value is numeric."""
    try:
        float(value)
    except ValueError, TypeError:
        return False
    else:
        return True


class BMWCarDataSensor(CoordinatorEntity[BMWCarDataCoordinator], SensorEntity):
    """Sensor entity for BMW CarData telematics data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BMWCarDataCoordinator,
        vin: str,
        descriptor_name: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._descriptor_name = descriptor_name
        self._attr_unique_id = f"{vin}_{description.key}"
        self._update_device_info()

    def _update_device_info(self) -> None:
        """Set device info from vehicle data."""
        vehicle = self._get_vehicle()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._vin)},
            name=f"BMW {vehicle.model_name}" if vehicle else f"BMW ({self._vin[-6:]})",
            manufacturer="BMW",
            model=vehicle.model_name if vehicle else None,
            sw_version=vehicle.pu_step if vehicle else None,
            hw_version=vehicle.head_unit if vehicle else None,
        )

    def _get_vehicle(self) -> Any:
        """Get the vehicle object."""
        if self.coordinator.data and self._vin in self.coordinator.data.vehicles:
            return self.coordinator.data.vehicles[self._vin].vehicle
        return None

    @property
    def native_value(self) -> str | float | None:
        """Return the sensor value."""
        entry = self._get_telematic_entry()
        if entry is None:
            return None

        value = entry.value
        if _is_numeric(value):
            float_val = float(value)
            # Return int if it's a whole number
            if float_val == int(float_val):
                return int(float_val)
            return round(float_val, 2)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        entry = self._get_telematic_entry()
        if entry is None:
            return None
        return {
            "descriptor": self._descriptor_name,
            "timestamp": entry.timestamp,
            "raw_value": entry.value,
            "unit": entry.unit,
        }

    def _get_telematic_entry(self) -> Any:
        """Get the telematic data entry for this sensor."""
        if self.coordinator.data and self._vin in self.coordinator.data.vehicles:
            return self.coordinator.data.vehicles[self._vin].telematic_data.get(
                self._descriptor_name
            )
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

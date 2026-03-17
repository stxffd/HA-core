"""Tests for BMW CarData binary sensor platform."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.bmw_cardata.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
)
from homeassistant.components.bmw_cardata.const import BINARY_DESCRIPTORS


class TestBinarySensorDescriptions:
    """Tests for binary sensor description definitions."""

    def test_all_binary_descriptors_have_description(self) -> None:
        """Every descriptor in BINARY_DESCRIPTORS should have a description."""
        for descriptor in BINARY_DESCRIPTORS:
            assert descriptor in BINARY_SENSOR_DESCRIPTIONS, (
                f"Missing description for {descriptor}"
            )

    def test_door_sensors_have_door_device_class(self) -> None:
        """Door sensors should have DOOR device class."""
        door_keys = [
            "vehicle.cabin.door.row1.driver.isOpen",
            "vehicle.cabin.door.row1.passenger.isOpen",
            "vehicle.cabin.door.row2.driver.isOpen",
            "vehicle.cabin.door.row2.passenger.isOpen",
        ]

        for key in door_keys:
            desc = BINARY_SENSOR_DESCRIPTIONS[key]
            assert desc.device_class == BinarySensorDeviceClass.DOOR

    def test_lock_sensors_have_lock_device_class(self) -> None:
        """Lock sensors should have LOCK device class."""
        lock_keys = [
            "vehicle.cabin.door.row1.driver.isLocked",
            "vehicle.cabin.door.row1.passenger.isLocked",
            "vehicle.cabin.door.row2.driver.isLocked",
            "vehicle.cabin.door.row2.passenger.isLocked",
        ]

        for key in lock_keys:
            desc = BINARY_SENSOR_DESCRIPTIONS[key]
            assert desc.device_class == BinarySensorDeviceClass.LOCK

    def test_window_sensors_have_window_device_class(self) -> None:
        """Window sensors should have WINDOW device class."""
        window_keys = [
            "vehicle.cabin.door.row1.driver.window.isOpen",
            "vehicle.cabin.door.row1.passenger.window.isOpen",
            "vehicle.cabin.door.row2.driver.window.isOpen",
            "vehicle.cabin.door.row2.passenger.window.isOpen",
        ]

        for key in window_keys:
            desc = BINARY_SENSOR_DESCRIPTIONS[key]
            assert desc.device_class == BinarySensorDeviceClass.WINDOW

    def test_trunk_and_hood_have_opening_device_class(self) -> None:
        """Trunk and hood should have OPENING device class."""
        assert (
            BINARY_SENSOR_DESCRIPTIONS["vehicle.body.trunk.isOpen"].device_class
            == BinarySensorDeviceClass.OPENING
        )
        assert (
            BINARY_SENSOR_DESCRIPTIONS["vehicle.body.hood.isOpen"].device_class
            == BinarySensorDeviceClass.OPENING
        )

    def test_moving_has_moving_device_class(self) -> None:
        """Moving sensor should have MOVING device class."""
        assert (
            BINARY_SENSOR_DESCRIPTIONS["vehicle.body.isMoving"].device_class
            == BinarySensorDeviceClass.MOVING
        )

    def test_all_descriptions_have_key(self) -> None:
        """All binary sensor descriptions should have a key."""
        for descriptor, desc in BINARY_SENSOR_DESCRIPTIONS.items():
            assert desc.key, f"Missing key for {descriptor}"

    def test_all_descriptions_have_translation_key(self) -> None:
        """All binary sensor descriptions should have a translation_key."""
        for descriptor, desc in BINARY_SENSOR_DESCRIPTIONS.items():
            assert desc.translation_key, f"Missing translation_key for {descriptor}"

    def test_description_count(self) -> None:
        """Verify expected number of binary sensor descriptions."""
        assert len(BINARY_SENSOR_DESCRIPTIONS) == 16
        assert len(BINARY_DESCRIPTORS) == 16

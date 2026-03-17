"""Tests for BMW CarData sensor platform."""

from __future__ import annotations

from custom_components.bmw_cardata.sensor import (
    SENSOR_DESCRIPTIONS,
    _format_descriptor_name,
    _is_numeric,
)


class TestSensorDescriptions:
    """Tests for sensor description definitions."""

    def test_mileage_sensor_exists(self) -> None:
        """Mileage sensor should be defined."""
        assert "vehicle.chassis.mileage" in SENSOR_DESCRIPTIONS
        desc = SENSOR_DESCRIPTIONS["vehicle.chassis.mileage"]
        assert desc.key == "mileage"
        assert desc.translation_key == "mileage"

    def test_battery_soc_sensor_exists(self) -> None:
        """Battery SoC sensor should be defined."""
        assert (
            "vehicle.powertrain.electric.battery.stateOfCharge" in SENSOR_DESCRIPTIONS
        )
        desc = SENSOR_DESCRIPTIONS["vehicle.powertrain.electric.battery.stateOfCharge"]
        assert desc.key == "battery_soc"

    def test_charging_power_sensor_exists(self) -> None:
        """Charging power sensor should be defined."""
        assert (
            "vehicle.powertrain.electric.battery.charging.power" in SENSOR_DESCRIPTIONS
        )

    def test_tyre_pressure_sensors_exist(self) -> None:
        """All four tyre pressure sensors should be defined."""
        expected = [
            "vehicle.chassis.axle.row1.wheel.left.tire.pressure",
            "vehicle.chassis.axle.row1.wheel.right.tire.pressure",
            "vehicle.chassis.axle.row2.wheel.left.tire.pressure",
            "vehicle.chassis.axle.row2.wheel.right.tire.pressure",
        ]
        for key in expected:
            assert key in SENSOR_DESCRIPTIONS

    def test_all_descriptions_have_key(self) -> None:
        """All sensor descriptions should have a key."""
        for descriptor, desc in SENSOR_DESCRIPTIONS.items():
            assert desc.key, f"Missing key for {descriptor}"

    def test_description_count(self) -> None:
        """Verify expected number of sensor descriptions."""
        assert len(SENSOR_DESCRIPTIONS) >= 16


class TestFormatDescriptorName:
    """Tests for _format_descriptor_name helper."""

    def test_simple_descriptor(self) -> None:
        """Test simple descriptor formatting."""
        result = _format_descriptor_name("vehicle.chassis.mileage")
        assert result == "Chassis Mileage"

    def test_camel_case_splitting(self) -> None:
        """Test camelCase is split into words."""
        result = _format_descriptor_name("vehicle.cabin.door.row1.driver.isOpen")
        assert "Is" in result
        assert "Open" in result

    def test_strips_vehicle_prefix(self) -> None:
        """Test vehicle. prefix is removed."""
        result = _format_descriptor_name("vehicle.body.trunk.isOpen")
        assert not result.startswith("Vehicle")

    def test_nested_path(self) -> None:
        """Test deeply nested path formatting."""
        result = _format_descriptor_name(
            "vehicle.powertrain.electric.battery.stateOfCharge"
        )
        assert "Powertrain" in result
        assert "State" in result
        assert "Of" in result
        assert "Charge" in result


class TestIsNumeric:
    """Tests for _is_numeric helper."""

    def test_integer_string(self) -> None:
        """Integer string is numeric."""
        assert _is_numeric("42") is True

    def test_float_string(self) -> None:
        """Float string is numeric."""
        assert _is_numeric("3.14") is True

    def test_negative_number(self) -> None:
        """Negative number string is numeric."""
        assert _is_numeric("-5.5") is True

    def test_non_numeric_string(self) -> None:
        """Non-numeric string is not numeric."""
        assert _is_numeric("hello") is False

    def test_empty_string(self) -> None:
        """Empty string is not numeric."""
        assert _is_numeric("") is False

    def test_none(self) -> None:
        """None is not numeric."""
        assert _is_numeric(None) is False

    def test_boolean_string(self) -> None:
        """Boolean string is not numeric."""
        assert _is_numeric("true") is False
        assert _is_numeric("false") is False

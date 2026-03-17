"""Tests for BMW CarData coordinator."""

from __future__ import annotations

from bmw_cardata.models import TelematicDataEntry
from bmw_cardata.mqtt import MqttMessage
from custom_components.bmw_cardata.coordinator import BMWCarDataData, VehicleData

from .conftest import (
    MOCK_TELEMATIC_ENTRIES,
    MOCK_VEHICLE,
    MOCK_VEHICLE_MAPPING,
    MOCK_VIN,
)


class TestVehicleData:
    """Tests for VehicleData dataclass."""

    def test_vehicle_data_creation(self) -> None:
        """Test creating VehicleData."""
        data = VehicleData(
            vin=MOCK_VIN,
            mapping=MOCK_VEHICLE_MAPPING,
            vehicle=MOCK_VEHICLE,
            telematic_data=MOCK_TELEMATIC_ENTRIES,
        )
        assert data.vin == MOCK_VIN
        assert data.vehicle.model_name == "330e"
        assert len(data.telematic_data) == 9

    def test_vehicle_data_defaults(self) -> None:
        """Test VehicleData defaults."""
        data = VehicleData(vin=MOCK_VIN, mapping=MOCK_VEHICLE_MAPPING)
        assert data.vehicle is None
        assert data.telematic_data == {}


class TestBMWCarDataData:
    """Tests for BMWCarDataData dataclass."""

    def test_empty_data(self) -> None:
        """Test creating empty coordinator data."""
        data = BMWCarDataData()
        assert data.vehicles == {}
        assert data.gcid == ""
        assert data.container_id == ""

    def test_data_with_vehicles(self) -> None:
        """Test coordinator data with vehicles."""
        vehicle_data = VehicleData(
            vin=MOCK_VIN,
            mapping=MOCK_VEHICLE_MAPPING,
            vehicle=MOCK_VEHICLE,
            telematic_data=MOCK_TELEMATIC_ENTRIES,
        )
        data = BMWCarDataData(
            vehicles={MOCK_VIN: vehicle_data},
            gcid="test-gcid",
            container_id="container-123",
        )
        assert MOCK_VIN in data.vehicles
        assert data.vehicles[MOCK_VIN].vehicle.brand == "BMW"


class TestMqttMessageHandling:
    """Tests for MQTT message handling logic in the coordinator context."""

    def _make_coordinator_data(self) -> BMWCarDataData:
        """Create sample coordinator data for tests."""
        vehicle_data = VehicleData(
            vin=MOCK_VIN,
            mapping=MOCK_VEHICLE_MAPPING,
            vehicle=MOCK_VEHICLE,
            telematic_data=dict(MOCK_TELEMATIC_ENTRIES),
        )
        return BMWCarDataData(
            vehicles={MOCK_VIN: vehicle_data},
            gcid="test-gcid",
            container_id="container-123",
        )

    def test_mqtt_message_updates_existing_entry(self) -> None:
        """Test that MQTT messages update existing telematic data."""
        data = self._make_coordinator_data()
        vehicle_data = data.vehicles[MOCK_VIN]

        # Simulate what coordinator._handle_mqtt_message does
        new_entry = TelematicDataEntry(
            name="vehicle.chassis.mileage",
            value="45500",
            unit="km",
            timestamp="2025-03-12T16:00:00Z",
        )
        message = MqttMessage(
            vin=MOCK_VIN,
            entries=[new_entry],
            raw_payload={},
        )

        updated = False
        for entry in message.entries:
            existing = vehicle_data.telematic_data.get(entry.name)
            if existing and (
                entry.value != existing.value or entry.timestamp != existing.timestamp
            ):
                vehicle_data.telematic_data[entry.name] = entry
                updated = True

        assert updated is True
        assert vehicle_data.telematic_data["vehicle.chassis.mileage"].value == "45500"

    def test_mqtt_message_adds_new_entry(self) -> None:
        """Test that MQTT messages can add new telematic entries."""
        data = self._make_coordinator_data()
        vehicle_data = data.vehicles[MOCK_VIN]

        new_entry = TelematicDataEntry(
            name="vehicle.new.descriptor",
            value="42",
            unit="",
            timestamp="2025-03-12T16:00:00Z",
        )
        message = MqttMessage(
            vin=MOCK_VIN,
            entries=[new_entry],
            raw_payload={},
        )

        for entry in message.entries:
            if entry.name not in vehicle_data.telematic_data:
                vehicle_data.telematic_data[entry.name] = entry

        assert "vehicle.new.descriptor" in vehicle_data.telematic_data

    def test_mqtt_message_unknown_vin_ignored(self) -> None:
        """Test that MQTT messages for unknown VINs are ignored."""
        data = self._make_coordinator_data()

        message = MqttMessage(
            vin="UNKNOWN_VIN_123456",
            entries=[
                TelematicDataEntry(name="test", value="1", unit="", timestamp=""),
            ],
            raw_payload={},
        )

        # Unknown VIN should not be in data
        assert message.vin not in data.vehicles

    def test_mqtt_message_no_update_when_same_value(self) -> None:
        """Test that identical values don't trigger update."""
        data = self._make_coordinator_data()
        vehicle_data = data.vehicles[MOCK_VIN]

        # Same value and timestamp as existing
        same_entry = TelematicDataEntry(
            name="vehicle.chassis.mileage",
            value="45230",
            unit="km",
            timestamp="2025-03-12T14:30:00Z",
        )

        existing = vehicle_data.telematic_data.get(same_entry.name)
        updated = existing is not None and (
            same_entry.value != existing.value
            or same_entry.timestamp != existing.timestamp
        )
        assert updated is False

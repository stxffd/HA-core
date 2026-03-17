"""Shared test fixtures for BMW CarData HA integration tests."""

from __future__ import annotations

from bmw_cardata.models import TelematicDataEntry, Vehicle, VehicleMapping

# ── Config entry mock data ──────────────────────────────────────────

MOCK_CONFIG_DATA = {
    "client_id": "test-client-id-1234567890",
    "access_token": "test-access-token",
    "refresh_token": "test-refresh-token",
    "id_token": "test-id-token",
    "gcid": "test-gcid-12345",
    "token_expires_at": 9999999999,  # Far future
    "container_id": "container-123",
}

MOCK_VIN = "WBA12345678901234"

MOCK_VEHICLE = Vehicle(
    vin=MOCK_VIN,
    brand="BMW",
    model_name="330e",
    model_range="3er",
    series="3",
    body_type="G20",
    drive_train="PHEV_OTTO",
    propulsion_type="PHEV",
    head_unit="MGU",
    is_telematics_capable=True,
    number_of_doors=4,
    has_navi=True,
    has_sun_roof=False,
    steering="LEFT",
    engine="B48",
    colour_code="475",
    construction_date="2023-06-15",
    country_code_iso="DE",
    pu_step="0723",
    model_key="3X31",
)

MOCK_VEHICLE_MAPPING = VehicleMapping(
    vin=MOCK_VIN,
    mapped_since="2024-01-15T10:00:00Z",
    mapping_type="PRIMARY",
)

MOCK_TELEMATIC_ENTRIES = {
    "vehicle.chassis.mileage": TelematicDataEntry(
        name="vehicle.chassis.mileage",
        value="45230",
        unit="km",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.powertrain.electric.battery.stateOfCharge": TelematicDataEntry(
        name="vehicle.powertrain.electric.battery.stateOfCharge",
        value="72",
        unit="%",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.powertrain.combustionEngine.remainingFuelLiters": TelematicDataEntry(
        name="vehicle.powertrain.combustionEngine.remainingFuelLiters",
        value="35.5",
        unit="l",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.cabin.door.row1.driver.isOpen": TelematicDataEntry(
        name="vehicle.cabin.door.row1.driver.isOpen",
        value="false",
        unit="",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.cabin.door.row1.driver.isLocked": TelematicDataEntry(
        name="vehicle.cabin.door.row1.driver.isLocked",
        value="true",
        unit="",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.cabin.infotainment.navigation.currentLocation.latitude": TelematicDataEntry(
        name="vehicle.cabin.infotainment.navigation.currentLocation.latitude",
        value="48.137154",
        unit="°",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.cabin.infotainment.navigation.currentLocation.longitude": TelematicDataEntry(
        name="vehicle.cabin.infotainment.navigation.currentLocation.longitude",
        value="11.576124",
        unit="°",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.cabin.infotainment.navigation.currentLocation.heading": TelematicDataEntry(
        name="vehicle.cabin.infotainment.navigation.currentLocation.heading",
        value="180.5",
        unit="°",
        timestamp="2025-03-12T14:30:00Z",
    ),
    "vehicle.body.trunk.isOpen": TelematicDataEntry(
        name="vehicle.body.trunk.isOpen",
        value="false",
        unit="",
        timestamp="2025-03-12T14:30:00Z",
    ),
}

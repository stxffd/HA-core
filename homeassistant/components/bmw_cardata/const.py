"""Constants for the BMW CarData integration."""

from homeassistant.const import Platform

DOMAIN = "bmw_cardata"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
]

# Config entry keys
CONF_CLIENT_ID = "client_id"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ID_TOKEN = "id_token"
CONF_GCID = "gcid"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
CONF_CONTAINER_ID = "container_id"
CONF_MQTT_ENABLED = "mqtt_enabled"

# Container settings
CONTAINER_NAME = "HomeAssistant"
CONTAINER_PURPOSE = "Home Assistant BMW CarData Integration"

# Polling interval (API rate limit: 50 req/day)
DEFAULT_SCAN_INTERVAL_MINUTES = 30

# Telematic descriptor sets for platform routing
BINARY_DESCRIPTORS: frozenset[str] = frozenset(
    {
        "vehicle.cabin.door.row1.driver.isOpen",
        "vehicle.cabin.door.row1.passenger.isOpen",
        "vehicle.cabin.door.row2.driver.isOpen",
        "vehicle.cabin.door.row2.passenger.isOpen",
        "vehicle.cabin.door.row1.driver.isLocked",
        "vehicle.cabin.door.row1.passenger.isLocked",
        "vehicle.cabin.door.row2.driver.isLocked",
        "vehicle.cabin.door.row2.passenger.isLocked",
        "vehicle.cabin.door.row1.driver.window.isOpen",
        "vehicle.cabin.door.row1.passenger.window.isOpen",
        "vehicle.cabin.door.row2.driver.window.isOpen",
        "vehicle.cabin.door.row2.passenger.window.isOpen",
        "vehicle.body.trunk.isOpen",
        "vehicle.body.hood.isOpen",
        "vehicle.body.isMoving",
        "vehicle.cabin.parkingBrake.isActive",
    }
)

# Location descriptors handled by device_tracker (skipped by sensor platform)
LOCATION_DESCRIPTORS: frozenset[str] = frozenset(
    {
        "vehicle.cabin.infotainment.navigation.currentLocation.latitude",
        "vehicle.cabin.infotainment.navigation.currentLocation.longitude",
    }
)

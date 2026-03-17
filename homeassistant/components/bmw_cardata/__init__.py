"""BMW CarData integration for Home Assistant."""

from __future__ import annotations

import logging

from bmw_cardata.exceptions import BMWCarDataError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_MQTT_ENABLED, PLATFORMS
from .coordinator import BMWCarDataCoordinator

_LOGGER = logging.getLogger(__name__)

type BMWCarDataConfigEntry = ConfigEntry[BMWCarDataCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BMWCarDataConfigEntry) -> bool:
    """Set up BMW CarData from a config entry."""
    coordinator = BMWCarDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start MQTT streaming if enabled in options
    if entry.options.get(CONF_MQTT_ENABLED, False):
        try:
            await coordinator.async_start_mqtt()
        except BMWCarDataError, OSError:
            _LOGGER.warning("Failed to start MQTT streaming, falling back to polling")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BMWCarDataConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: BMWCarDataCoordinator = entry.runtime_data

    # Stop MQTT streaming
    await coordinator.async_stop_mqtt()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

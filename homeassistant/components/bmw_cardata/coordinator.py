"""DataUpdateCoordinator for BMW CarData integration.

Handles:
- Token refresh (access token expires every hour)
- Container management (ensure a container exists)
- Periodic polling of vehicle telematics data
- Vehicle discovery and basic data retrieval
- Optional MQTT streaming for real-time updates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
import time

from aiohttp import ClientSession
from bmw_cardata.api import CarDataApiClient
from bmw_cardata.auth import AbstractAuth, DeviceAuth
from bmw_cardata.exceptions import (
    AuthenticationError,
    BMWCarDataError,
    RateLimitError,
    TokenExpiredError,
)
from bmw_cardata.models import (
    ChargingSession,
    LocationBasedChargingSetting,
    TelematicDataEntry,
    TyreDiagnosis,
    Vehicle,
    VehicleMapping,
)
from bmw_cardata.mqtt import CarDataMqttClient, MqttMessage

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CONTAINER_ID,
    CONF_GCID,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    CONTAINER_NAME,
    CONTAINER_PURPOSE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VehicleData:
    """Data for a single vehicle."""

    vin: str
    mapping: VehicleMapping
    vehicle: Vehicle | None = None
    telematic_data: dict[str, TelematicDataEntry] = field(default_factory=dict)
    charging_sessions: list[ChargingSession] = field(default_factory=list)
    charging_settings: list[LocationBasedChargingSetting] = field(default_factory=list)
    tyre_diagnosis: TyreDiagnosis | None = None


@dataclass
class BMWCarDataData:
    """Data returned by the coordinator."""

    vehicles: dict[str, VehicleData] = field(default_factory=dict)
    gcid: str = ""
    container_id: str = ""


class ConfigEntryAuth(AbstractAuth):
    """Auth implementation that reads tokens from config entry and auto-refreshes."""

    def __init__(
        self,
        websession: ClientSession,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize config entry auth."""
        super().__init__(websession)
        self._hass = hass
        self._entry = entry

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        token_expires_at = self._entry.data.get(CONF_TOKEN_EXPIRES_AT, 0)

        # Refresh if token expires within 5 minutes
        if time.time() > (token_expires_at - 300):
            await self._refresh_token()

        return self._entry.data[CONF_ACCESS_TOKEN]

    async def _refresh_token(self) -> None:
        """Refresh the access token using the refresh token."""
        client_id = self._entry.data[CONF_CLIENT_ID]
        refresh_token = self._entry.data[CONF_REFRESH_TOKEN]

        device_auth = DeviceAuth(self.websession)

        try:
            tokens = await device_auth.refresh_tokens(client_id, refresh_token)
        except TokenExpiredError as err:
            # Refresh token expired - need full reauth
            raise ConfigEntryAuthFailed(
                "BMW CarData refresh token expired. Please re-authenticate."
            ) from err
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                f"BMW CarData authentication failed: {err}"
            ) from err

        # Update the config entry with new tokens
        self._hass.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                CONF_ACCESS_TOKEN: tokens.access_token,
                CONF_REFRESH_TOKEN: tokens.refresh_token,
                CONF_ID_TOKEN: tokens.id_token,
                CONF_GCID: tokens.gcid or self._entry.data.get(CONF_GCID, ""),
                CONF_TOKEN_EXPIRES_AT: time.time() + tokens.expires_in,
            },
        )


class BMWCarDataCoordinator(DataUpdateCoordinator[BMWCarDataData]):
    """Coordinator for BMW CarData that manages API polling."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
            always_update=False,
        )

        session = async_get_clientsession(hass)
        self._auth = ConfigEntryAuth(session, hass, entry)
        self._api = CarDataApiClient(self._auth)
        self._container_id: str = entry.data.get(CONF_CONTAINER_ID, "")
        self._vehicles_discovered = False
        self._mqtt_client: CarDataMqttClient | None = None

    @property
    def api(self) -> CarDataApiClient:
        """Return the API client."""
        return self._api

    @property
    def mqtt_connected(self) -> bool:
        """Return True if MQTT streaming is active."""
        return self._mqtt_client is not None and self._mqtt_client.connected

    async def _async_setup(self) -> None:
        """Set up the coordinator (called once during first refresh).

        Discovers vehicles and ensures a container exists.
        """
        # Ensure a telematics container exists
        if not self._container_id:
            try:
                container = await self._api.ensure_container(
                    name=CONTAINER_NAME,
                    purpose=CONTAINER_PURPOSE,
                )
                self._container_id = container.container_id

                # Persist container ID to config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        CONF_CONTAINER_ID: self._container_id,
                    },
                )
            except AuthenticationError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except BMWCarDataError as err:
                raise UpdateFailed(f"Failed to set up container: {err}") from err

    async def async_start_mqtt(self) -> None:
        """Start MQTT streaming for real-time updates."""
        if self._mqtt_client and self._mqtt_client.connected:
            return

        gcid = self.config_entry.data.get(CONF_GCID, "")

        if not gcid:
            _LOGGER.warning("Cannot start MQTT: no GCID available")
            return

        async def get_id_token() -> str:
            """Provide fresh id_token for MQTT auth."""
            # Ensure tokens are fresh by calling access_token (triggers refresh)
            await self._auth.async_get_access_token()
            return self.config_entry.data.get(CONF_ID_TOKEN, "")

        vins: list[str] = []
        if self.data:
            vins = list(self.data.vehicles.keys())

        self._mqtt_client = CarDataMqttClient(
            gcid=gcid,
            id_token_provider=get_id_token,
        )
        self._mqtt_client.set_callback(self._handle_mqtt_message)
        await self._mqtt_client.connect(vins=vins or None)
        _LOGGER.info("MQTT streaming started for BMW CarData")

    async def async_stop_mqtt(self) -> None:
        """Stop MQTT streaming."""
        if self._mqtt_client:
            await self._mqtt_client.disconnect()
            self._mqtt_client = None
            _LOGGER.info("MQTT streaming stopped for BMW CarData")

    async def _handle_mqtt_message(self, message: MqttMessage) -> None:
        """Handle incoming MQTT streaming message and update coordinator data."""
        if not self.data:
            return

        vin = message.vin
        if vin not in self.data.vehicles:
            _LOGGER.debug("Received MQTT data for unknown VIN: %s", vin)
            return

        vehicle_data = self.data.vehicles[vin]
        updated = False

        for entry in message.entries:
            if entry.name in vehicle_data.telematic_data:
                existing = vehicle_data.telematic_data[entry.name]
                if (
                    entry.value != existing.value
                    or entry.timestamp != existing.timestamp
                ):
                    vehicle_data.telematic_data[entry.name] = entry
                    updated = True
            else:
                vehicle_data.telematic_data[entry.name] = entry
                updated = True

        if updated:
            self.async_set_updated_data(self.data)

    async def _async_update_data(self) -> BMWCarDataData:
        """Fetch data from BMW CarData API.

        This is called periodically by the coordinator.
        """
        data = BMWCarDataData(
            gcid=self.config_entry.data.get(CONF_GCID, ""),
            container_id=self._container_id,
        )

        try:
            # Get vehicle mappings
            mappings = await self._api.get_vehicle_mappings()

            for mapping in mappings:
                if mapping.mapping_type != "PRIMARY":
                    continue  # Only primary mappings can access data

                vin = mapping.vin
                vehicle_data = VehicleData(vin=vin, mapping=mapping)

                # Fetch basic data (only on first discovery or periodically)
                if not self._vehicles_discovered:
                    try:
                        vehicle_data.vehicle = await self._api.get_basic_data(vin)
                    except BMWCarDataError:
                        _LOGGER.warning("Failed to get basic data for VIN %s", vin)

                elif self.data and vin in self.data.vehicles:
                    # Reuse existing basic data
                    vehicle_data.vehicle = self.data.vehicles[vin].vehicle

                # Fetch telematics data
                if self._container_id:
                    try:
                        entries = await self._api.get_telematic_data(
                            vin, self._container_id
                        )
                        vehicle_data.telematic_data = {
                            entry.name: entry for entry in entries
                        }
                    except RateLimitError:
                        _LOGGER.warning("Rate limit reached, will retry next interval")
                        # Return existing data if available
                        if self.data and vin in self.data.vehicles:
                            vehicle_data.telematic_data = self.data.vehicles[
                                vin
                            ].telematic_data
                    except BMWCarDataError:
                        _LOGGER.warning("Failed to get telematics for VIN %s", vin)

                # Fetch charging history (last 30 days)
                try:
                    now = datetime.now(UTC)
                    from_dt = now - timedelta(days=30)
                    vehicle_data.charging_sessions = (
                        await self._api.get_charging_history(vin, from_dt, now)
                    )
                except BMWCarDataError:
                    _LOGGER.debug("Failed to get charging history for VIN %s", vin)

                # Fetch location-based charging settings
                try:
                    vehicle_data.charging_settings = (
                        await self._api.get_location_based_charging_settings(vin)
                    )
                except BMWCarDataError:
                    _LOGGER.debug("Failed to get charging settings for VIN %s", vin)

                # Fetch tyre diagnosis
                try:
                    vehicle_data.tyre_diagnosis = await self._api.get_tyre_diagnosis(
                        vin
                    )
                except BMWCarDataError:
                    _LOGGER.debug("Failed to get tyre diagnosis for VIN %s", vin)

                data.vehicles[vin] = vehicle_data

            self._vehicles_discovered = True

        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RateLimitError as err:
            raise UpdateFailed(retry_after=3600) from err
        except BMWCarDataError as err:
            raise UpdateFailed(
                f"Error communicating with BMW CarData API: {err}"
            ) from err

        return data

"""Config flow for BMW CarData integration.

Implements the OAuth 2.0 Device Authorization Grant (RFC 8628) flow:
1. User enters their BMW CarData Client ID
2. Integration initiates device code flow
3. User opens verification URL and enters code on BMW website
4. Integration polls for token completion
5. Tokens are stored in the config entry
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
import time
from typing import Any

from aiohttp import ClientError
from bmw_cardata.auth import DeviceAuth
from bmw_cardata.exceptions import (
    AuthenticationError,
    AuthorizationPendingError,
    DeviceCodeExpiredError,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_GCID,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
    }
)


class BMWCarDataConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BMW CarData."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client_id: str = ""
        self._device_code: str = ""
        self._code_verifier: str = ""
        self._verification_uri: str = ""
        self._user_code: str = ""
        self._interval: int = 5

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where user enters Client ID."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()

            if not client_id or len(client_id) < 10:
                errors["base"] = "invalid_client_id"
            else:
                self._client_id = client_id

                try:
                    session = async_get_clientsession(self.hass)
                    device_auth = DeviceAuth(session)
                    code_response = await device_auth.request_device_code(client_id)

                    self._device_code = code_response.device_code
                    self._code_verifier = code_response.code_verifier
                    self._verification_uri = code_response.verification_uri
                    self._user_code = code_response.user_code
                    self._interval = code_response.interval

                    return await self.async_step_authorize()

                except ClientError:
                    errors["base"] = "cannot_connect"
                except AuthenticationError:
                    errors["base"] = "auth_failed"
                except Exception:
                    _LOGGER.exception("Unexpected error during device code request")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the authorization step with verification URI and user code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User clicked submit - try to exchange the device code for tokens
            try:
                session = async_get_clientsession(self.hass)
                device_auth = DeviceAuth(session)

                tokens = await device_auth.exchange_device_code(
                    client_id=self._client_id,
                    device_code=self._device_code,
                    code_verifier=self._code_verifier,
                )

                # Set unique ID based on GCID (account identifier)
                gcid = tokens.gcid
                if gcid:
                    await self.async_set_unique_id(gcid)
                    self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"BMW CarData ({gcid[:8]}...)" if gcid else "BMW CarData",
                    data={
                        CONF_CLIENT_ID: self._client_id,
                        CONF_ACCESS_TOKEN: tokens.access_token,
                        CONF_REFRESH_TOKEN: tokens.refresh_token,
                        CONF_ID_TOKEN: tokens.id_token,
                        CONF_GCID: gcid,
                        CONF_TOKEN_EXPIRES_AT: time.time() + tokens.expires_in,
                    },
                )

            except AuthorizationPendingError:
                errors["base"] = "auth_timeout"
            except DeviceCodeExpiredError:
                errors["base"] = "auth_timeout"
            except AuthenticationError:
                errors["base"] = "auth_failed"
            except ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during token exchange")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="authorize",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "verification_uri": self._verification_uri,
                "user_code": self._user_code,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when tokens expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication and restart device code flow."""
        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            self._client_id = reauth_entry.data[CONF_CLIENT_ID]

            try:
                session = async_get_clientsession(self.hass)
                device_auth = DeviceAuth(session)
                code_response = await device_auth.request_device_code(self._client_id)

                self._device_code = code_response.device_code
                self._code_verifier = code_response.code_verifier
                self._verification_uri = code_response.verification_uri
                self._user_code = code_response.user_code
                self._interval = code_response.interval

                return await self.async_step_authorize_reauth()
            except Exception:
                _LOGGER.exception("Error during reauth device code request")
                return self.async_abort(reason="unknown")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
        )

    async def async_step_authorize_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth authorization step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                device_auth = DeviceAuth(session)

                tokens = await device_auth.exchange_device_code(
                    client_id=self._client_id,
                    device_code=self._device_code,
                    code_verifier=self._code_verifier,
                )

                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={
                        CONF_ACCESS_TOKEN: tokens.access_token,
                        CONF_REFRESH_TOKEN: tokens.refresh_token,
                        CONF_ID_TOKEN: tokens.id_token,
                        CONF_GCID: tokens.gcid,
                        CONF_TOKEN_EXPIRES_AT: time.time() + tokens.expires_in,
                    },
                )

            except AuthorizationPendingError:
                errors["base"] = "auth_timeout"
            except DeviceCodeExpiredError:
                errors["base"] = "auth_timeout"
            except AuthenticationError:
                errors["base"] = "auth_failed"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth token exchange")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="authorize",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "verification_uri": self._verification_uri,
                "user_code": self._user_code,
            },
        )

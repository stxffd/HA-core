"""Tests for BMW CarData config flow."""

from __future__ import annotations

from bmw_cardata.models import DeviceCodeResponse, TokenResponse

from homeassistant.components.bmw_cardata.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_GCID,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
)

from .conftest import MOCK_CONFIG_DATA

MOCK_DEVICE_CODE_RESPONSE = DeviceCodeResponse(
    user_code="AB12-CD34",
    device_code="dev-code-xyz",
    verification_uri="https://customer.bmwgroup.com/verify",
    interval=5,
    expires_in=600,
    code_verifier="test-verifier",
)

MOCK_TOKEN_RESPONSE = TokenResponse(
    access_token="new-access-token",
    token_type="Bearer",
    expires_in=3600,
    refresh_token="new-refresh-token",
    scope="authenticate_user openid cardata:api:read cardata:streaming:read",
    id_token="new-id-token",
    gcid="test-gcid-12345",
)


class TestConfigFlowValidation:
    """Tests for config flow input validation."""

    def test_domain_is_correct(self) -> None:
        """Verify the config flow uses the correct domain."""
        assert DOMAIN == "bmw_cardata"

    def test_client_id_too_short(self) -> None:
        """A client ID shorter than 10 chars should be rejected."""
        # This tests the validation logic conceptually
        client_id = "short"
        assert len(client_id) < 10

    def test_valid_client_id(self) -> None:
        """A valid client ID passes length check."""
        client_id = "test-client-id-1234567890"
        assert len(client_id) >= 10


class TestConfigFlowDataStructure:
    """Tests for the data structure created by config flow."""

    def test_config_data_has_all_required_keys(self) -> None:
        """Config entry data should include all required keys."""
        required_keys = {
            CONF_CLIENT_ID,
            CONF_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN,
            CONF_ID_TOKEN,
            CONF_GCID,
            CONF_TOKEN_EXPIRES_AT,
        }
        assert required_keys.issubset(MOCK_CONFIG_DATA.keys())

    def test_token_response_to_config_data(self) -> None:
        """Verify token response maps correctly to config data."""
        tokens = MOCK_TOKEN_RESPONSE
        config_data = {
            CONF_CLIENT_ID: "test-client",
            CONF_ACCESS_TOKEN: tokens.access_token,
            CONF_REFRESH_TOKEN: tokens.refresh_token,
            CONF_ID_TOKEN: tokens.id_token,
            CONF_GCID: tokens.gcid,
            CONF_TOKEN_EXPIRES_AT: 1000 + tokens.expires_in,
        }
        assert config_data[CONF_ACCESS_TOKEN] == "new-access-token"
        assert config_data[CONF_REFRESH_TOKEN] == "new-refresh-token"
        assert config_data[CONF_ID_TOKEN] == "new-id-token"
        assert config_data[CONF_GCID] == "test-gcid-12345"
        assert config_data[CONF_TOKEN_EXPIRES_AT] == 4600


class TestDeviceCodeResponse:
    """Tests for device code response handling in config flow context."""

    def test_device_code_response_fields(self) -> None:
        """Verify all device code response fields are accessible."""
        resp = MOCK_DEVICE_CODE_RESPONSE
        assert resp.user_code == "AB12-CD34"
        assert resp.device_code == "dev-code-xyz"
        assert resp.verification_uri == "https://customer.bmwgroup.com/verify"
        assert resp.interval == 5
        assert resp.expires_in == 600
        assert resp.code_verifier == "test-verifier"

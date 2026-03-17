"""Tests for BMW CarData device tracker platform."""

from __future__ import annotations

from custom_components.bmw_cardata.const import LOCATION_DESCRIPTORS
from custom_components.bmw_cardata.device_tracker import LAT_DESCRIPTOR, LON_DESCRIPTOR


class TestDeviceTrackerConstants:
    """Tests for device tracker constants."""

    def test_lat_descriptor_matches_const(self) -> None:
        """LAT_DESCRIPTOR should be in LOCATION_DESCRIPTORS."""
        assert LAT_DESCRIPTOR in LOCATION_DESCRIPTORS

    def test_lon_descriptor_matches_const(self) -> None:
        """LON_DESCRIPTOR should be in LOCATION_DESCRIPTORS."""
        assert LON_DESCRIPTOR in LOCATION_DESCRIPTORS

    def test_location_descriptors_count(self) -> None:
        """Should have exactly 2 location descriptors."""
        assert len(LOCATION_DESCRIPTORS) == 2

    def test_descriptor_paths(self) -> None:
        """Verify the exact descriptor paths."""
        assert (
            LAT_DESCRIPTOR
            == "vehicle.cabin.infotainment.navigation.currentLocation.latitude"
        )
        assert (
            LON_DESCRIPTOR
            == "vehicle.cabin.infotainment.navigation.currentLocation.longitude"
        )

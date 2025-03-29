"""Models for mitsubishi_matouch integration."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL


@dataclass(slots=True)
class MAConfig:
    """Config for a single MA Touch device."""

    mac_address: str
    pin: str
    scan_interval: int = DEFAULT_SCAN_INTERVAL


@dataclass(slots=True)
class MAConfigEntryRuntimeData:
    """Config entry for a single MA Touch device."""

    config: MAConfig
    coordinator: DataUpdateCoordinator # cant use MACoordinator here due to cyclical import

type MAConfigEntry = ConfigEntry[MAConfigEntryRuntimeData]

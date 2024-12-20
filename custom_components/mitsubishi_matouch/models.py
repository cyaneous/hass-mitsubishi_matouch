"""Models for mitsubishi_matouch integration."""

from dataclasses import dataclass

from .btmatouch.thermostat import Thermostat

from .const import (
    DEFAULT_SCAN_INTERVAL,
)


@dataclass(slots=True)
class MAConfig:
    """Config for a single MA Touch device."""

    mac_address: str
    pin: str
    scan_interval: int = DEFAULT_SCAN_INTERVAL


@dataclass(slots=True)
class MAConfigEntryData:
    """Config entry for a single MA Touch device."""

    ma_config: MAConfig
    thermostat: Thermostat

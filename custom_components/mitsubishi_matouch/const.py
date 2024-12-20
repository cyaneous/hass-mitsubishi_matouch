"""Constants for the Mitsubishi MA Touch integration."""

from enum import Enum

from .btmatouch.const import MAOperationMode, MAFanMode

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
)

DOMAIN = "mitsubishi_matouch"

MANUFACTURER = "Mitsubishi Electric"
DEVICE_MODEL = "PAR-CT01MAU"

MA_TO_HA_HVAC: dict[MAOperationMode, HVACMode] = {
    MAOperationMode.OFF: HVACMode.OFF,
    MAOperationMode.AUTO: HVACMode.AUTO,
    MAOperationMode.HEAT: HVACMode.HEAT,
    MAOperationMode.COOL: HVACMode.COOL,
    MAOperationMode.DRY: HVACMode.DRY,
    MAOperationMode.FAN: HVACMode.FAN_ONLY,
}

HA_TO_MA_HVAC: dict[HVACMode, MAOperationMode] = {
    HVACMode.OFF: MAOperationMode.OFF,
    HVACMode.AUTO: MAOperationMode.AUTO,
    HVACMode.HEAT: MAOperationMode.HEAT,
    HVACMode.COOL: MAOperationMode.COOL,
    HVACMode.DRY: MAOperationMode.DRY,
    HVACMode.FAN_ONLY: MAOperationMode.FAN,
}

MA_TO_HA_FAN: dict[MAFanMode, str] = {
    MAFanMode.AUTO: FAN_AUTO,
    MAFanMode.HIGH: FAN_HIGH,
    MAFanMode.MEDIUM: FAN_MEDIUM,
    MAFanMode.LOW: FAN_LOW,
    MAFanMode.QUIET: "Quiet",
}

HA_TO_MA_FAN: dict[str, MAFanMode] = {
    FAN_AUTO: MAFanMode.AUTO,
    FAN_HIGH: MAFanMode.HIGH,
    FAN_MEDIUM: MAFanMode.MEDIUM,
    FAN_LOW: MAFanMode.LOW,
    "Quiet": MAFanMode.QUIET,
}

DEFAULT_SCAN_INTERVAL = 10 # seconds

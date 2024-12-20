"""Structures for the Mitsubishi MA Touch Thermostat."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Self

from construct import (
    Bytes,
    Const,
    Flag,
    Int8un,
    Int16un,
)
from construct_typed import (
    DataclassMixin,
    DataclassStruct,
    TEnum,
    TFlagsEnum,
    csfield,
)

from ._adapters import (
    _MATemperature,
)
from .const import (
    _MAMessageType,
    _MAResult,
    _MAOperationModeFlags,
    MAVaneMode,
    MAFanMode,
    _MAOtherFlags,
)

__all__: list[str] = []


class _MAStruct(DataclassMixin):
    """Structure for thermostat data."""

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Convert the data to a structure."""
        return DataclassStruct(cls).parse(data)

    def to_bytes(self) -> bytes:
        """Convert the structure to bytes."""
        return DataclassStruct(self.__class__).build(self)


@dataclass
class _MAMessageHeader(_MAStruct):
    """Message header.

    command header (length will be 2 + 1 + body.length + 2):
      length: 1 + body.length + 2
      message_id: uint8 (0 through 7?)
    """

    length: int = csfield(Int16un)
    message_id: int = csfield(Int8un)


@dataclass
class _MAMessageFooter(_MAStruct):
    """Message footer."""

    crc: int = csfield(Int16un)


@dataclass
class _MARequest(_MAStruct):
    """Request."""

    message_type: _MAMessageType = csfield(TEnum(Int16un, _MAMessageType))
    request_flag: int = csfield(Int8un) # request flag?


@dataclass
class _MAResponse(_MAStruct):
    """Response.

    05 00 02 00 <-- session time limit reached?
    05 09 02 00 10 54 89 00 <-- in menus
    """
    message_type: _MAMessageType = csfield(TEnum(Int8un, _MAMessageType))
    result: _MAResult = csfield(TEnum(Int8un, _MAResult))
    unknown_1: int = csfield(Int8un)
    unknown_2: int = csfield(Int8un)


@dataclass
class _MAAuthenticatedRequest(_MARequest):
    """Authenticated request with a PIN."""

    pin: int = csfield(Int16un)
    unknown_1: int = csfield(Const(0x00, Int8un))
    unknown_2: int = csfield(Const(0x00, Int8un))
    unknown_3: int = csfield(Const(0x00, Int8un))


@dataclass
class _MAStatusRequest(_MARequest):
    """Thermostat status request."""


@dataclass
class _MAStatusResponse(_MAResponse):
    """Thermostat status response.

    00 00 32 10 03 60 01 90 02 00 01 10 03 60 01 10 03 80 01 90 02 60 01 40 02 10 02 90 01 40 02 90 01 40 06 00 00 00 00 00 20 02 01 00 10 04
    """

    unknown_3: int = csfield(Int8un)
    unknown_4: int = csfield(Int8un)
    operation_mode_flags: _MAOperationModeFlags = csfield(TFlagsEnum(Int8un, _MAOperationModeFlags))
    max_cool_temperature: float = csfield(_MATemperature(Bytes(2)))
    min_cool_temperature: float = csfield(_MATemperature(Bytes(2)))
    max_heat_temperature: float = csfield(_MATemperature(Bytes(2)))
    min_heat_temperature: float = csfield(_MATemperature(Bytes(2)))
    max_unknown1_temperature: float = csfield(_MATemperature(Bytes(2)))
    min_unknown1_temperature: float = csfield(_MATemperature(Bytes(2)))
    max_unknown2_temperature: float = csfield(_MATemperature(Bytes(2)))
    min_unknown2_temperature: float = csfield(_MATemperature(Bytes(2)))
    max_unknown3_temperature: float = csfield(_MATemperature(Bytes(2)))
    min_unknown3_temperature: float = csfield(_MATemperature(Bytes(2)))
    cool_setpoint: float = csfield(_MATemperature(Bytes(2)))
    heat_setpoint: float = csfield(_MATemperature(Bytes(2)))
    unknown_setpoint_1: float = csfield(_MATemperature(Bytes(2)))
    unknown_setpoint_2: float = csfield(_MATemperature(Bytes(2)))
    unknown_setpoint_3: float = csfield(_MATemperature(Bytes(2)))
    fan_mode: MAFanMode = csfield(TEnum(Int8un, MAFanMode))
    vane_mode: MAVaneMode = csfield(TEnum(Int8un, MAVaneMode))
    unknown_5: int = csfield(Int8un)
    unknown_6: int = csfield(Int8un)
    unknown_7: int = csfield(Int8un)
    unknown_8: int = csfield(Int8un)
    hold: bool = csfield(Flag) # not sure if its only hold or flags
    room_temperature: float = csfield(_MATemperature(Bytes(2)))
    unknown_9: int = csfield(Int8un) # 0x01?
    unknown_10: int = csfield(Int8un) # 0x00?
    unknown_11: int = csfield(Int8un) # this and other_flags might be mixed up?
    other_flags: _MAOtherFlags = csfield(TFlagsEnum(Int8un, _MAOtherFlags)) # 0x00, 0x10, 0x14 or 0x04, etc: other_flags? bit2:temp_restriction, bit4: power


@dataclass
class _MAControlRequest(_MARequest):
    """Thermostat control request.

    off:        01 00 00 10 4502 1002 9001 4002 9001 6400 00
    on:         01 00 00 11 4502 1002 9001 4002 9001 6400 00
    mode auto:  02 00 00 79 4502 1002 9001 4002 9001 6400 00
    mode cool:  02 00 00 09 4502 1002 9001 4002 9001 6400 00
    mode heat:  02 00 00 11 4502 1002 9001 4002 9001 6400 00
    mode dry:   02 00 00 31 4502 1002 9001 4002 9001 6400 00
    mode fan:   02 00 00 01 4502 1002 9001 4002 9001 6400 00
    cool setp:  00 01 00 09 4002 1002 9001 4002 9001 6400 00
    heat setp:  00 02 00 11 4502 2002 9001 4002 9001 6400 00
    fan auto:   00 00 01 11 4502 1002 9001 4002 9001 6400 00
    fan high:   00 00 01 11 4502 1002 9001 4002 9001 6300 00
    fan medium: 00 00 01 11 4502 1002 9001 4002 9001 6200 00
    fan low:    00 00 01 11 4502 1002 9001 4002 9001 6000 00
    vane auto:  00 00 02 11 4502 1002 9001 4002 9001 6400 00
    vane swing: 00 00 02 11 4502 1002 9001 4002 9001 7400 00 <-- so 7 is vane, 4 is fan
    """
    
    flags_a: int = csfield(Int8un)
    flags_b: int = csfield(Int8un)
    flags_c: int = csfield(Int8un)
    operation_mode_flags: _MAOperationModeFlags = csfield(TFlagsEnum(Int8un, _MAOperationModeFlags))
    cool_setpoint: float = csfield(_MATemperature(Bytes(2)))
    heat_setpoint: float = csfield(_MATemperature(Bytes(2)))
    unknown_setpoint_1: float = csfield(_MATemperature(Bytes(2)))
    unknown_setpoint_2: float = csfield(_MATemperature(Bytes(2)))
    unknown_setpoint_3: float = csfield(_MATemperature(Bytes(2)))
    vane_fan_mode: int = csfield(Int8un)
    unknown_1: int = csfield(Const(0x00, Int8un))
    unknown_2: int = csfield(Const(0x00, Int8un))


@dataclass
class _MAControlResponse(_MAResponse):
    """Thermostat control response.

    succeeded: 00 00
    """

    unknown_1: int = csfield(Int8un)
    unknown_2: int = csfield(Int8un)


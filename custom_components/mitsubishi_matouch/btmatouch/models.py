"""Models for the btmatouch library."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ._structures import (
    _MAStruct,
    _MAStatusResponse,
)
from .const import (
    MAOperationMode,
    _MAOperationModeFlags,
    MAFanMode,
    MAVaneMode,
)

__all__ = [
    "Status",
]


@dataclass
class _BaseModel[StructType: _MAStruct](ABC):
    @classmethod
    @abstractmethod
    def _from_struct(cls: type[Self], struct: StructType) -> Self:
        """Convert the structure to a model."""

    @classmethod
    @abstractmethod
    def _struct_type(cls: type[Self]) -> type[StructType]:
        """Return the structure type associated with the model."""

    @classmethod
    def _from_bytes(cls: type[Self], data: bytes) -> Self:
        """Convert the data to a model."""
        return cls._from_struct(cls._struct_type().from_bytes(data))


@dataclass
class Status(_BaseModel[_MAStatusResponse]):
    """Status model."""

    max_cool_temperature: float
    min_cool_temperature: float
    max_heat_temperature: float
    min_heat_temperature: float
    cool_setpoint: float
    heat_setpoint: float
    auto_setpoint: float
    room_temperature: float
    fan_mode: MAFanMode
    vane_mode: MAVaneMode
    hold: bool
    operation_mode: MAOperationMode

    @classmethod
    def _from_struct(cls, struct: _MAStatusResponse) -> Self:
        return cls(
            max_cool_temperature=struct.max_cool_temperature,
            min_cool_temperature=struct.min_cool_temperature,
            max_heat_temperature=struct.max_heat_temperature,
            min_heat_temperature=struct.min_heat_temperature,
            max_auto_temperature=struct.max_auto_temperature,
            min_auto_temperature=struct.min_auto_temperature,
            cool_setpoint=struct.cool_setpoint,
            heat_setpoint=struct.heat_setpoint,
            room_temperature=struct.room_temperature,
            fan_mode=struct.fan_mode,
            vane_mode=struct.vane_mode,
            hold=struct.hold,
            operation_mode=MAOperationMode.AUTO if struct.operation_mode_flags & (_MAOperationModeFlags.FAN|_MAOperationModeFlags.AUTO) == (_MAOperationModeFlags.FAN|_MAOperationModeFlags.AUTO)
            else MAOperationMode.DRY if struct.operation_mode_flags & (_MAOperationModeFlags.FAN|_MAOperationModeFlags.DRY|_MAOperationModeFlags.HEAT) == (_MAOperationModeFlags.FAN|_MAOperationModeFlags.DRY|_MAOperationModeFlags.HEAT)
            else MAOperationMode.HEAT if struct.operation_mode_flags & (_MAOperationModeFlags.FAN|_MAOperationModeFlags.HEAT) == (_MAOperationModeFlags.FAN|_MAOperationModeFlags.HEAT)
            else MAOperationMode.COOL if struct.operation_mode_flags & (_MAOperationModeFlags.FAN|_MAOperationModeFlags.COOL) == (_MAOperationModeFlags.FAN|_MAOperationModeFlags.COOL)
            else MAOperationMode.FAN if struct.operation_mode_flags & _MAOperationModeFlags.FAN
            else MAOperationMode.OFF,
        )

    @classmethod
    def _struct_type(cls) -> type[_MAStatusResponse]:
        return _MAStatusResponse

"""Platform for Mitsubishi MA Touch climate entities."""

from typing import Any

from .btmatouch.const import MA_MIN_TEMP, MA_MAX_TEMP, MAOperationMode, MAVaneMode
from .btmatouch.exceptions import MAException
from .btmatouch.const import MAEvent
from .btmatouch.models import Status

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import SWING_ON, SWING_OFF
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MAConfigEntry
from .const import (
    DEVICE_MODEL,
    MANUFACTURER,
    MA_TO_HA_HVAC,
    HA_TO_MA_HVAC,
    MA_TO_HA_FAN,
    HA_TO_MA_FAN,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: MAConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Handle config entry setup."""

    async_add_entities(
        [MAClimate(entry)],
    )


class MAClimate(ClimateEntity):
    """Climate entity to represent an MA Touch thermostat."""

    _attr_entity_has_name = True
    _attr_name = None
    _attr_should_poll = False

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_precision = PRECISION_HALVES
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MA_MIN_TEMP
    _attr_max_temp = MA_MAX_TEMP
    _attr_hvac_modes = list(HA_TO_MA_HVAC.keys())
    _attr_fan_modes = list(HA_TO_MA_FAN.keys())
    _attr_swing_modes = [SWING_ON, SWING_OFF]

    _attr_available = False
    _attr_hvac_mode: HVACMode | None = None
    _attr_hvac_action: HVACAction | None = None
    _attr_target_temperature: float | None = None
    _attr_target_temperature_high: float | None = None
    _attr_target_temperature_low: float | None = None
    _attr_fan_mode: str | None = None
    _attr_swing_mode: str | None = None

    def __init__(self, entry: MAConfigEntry) -> None:
        """Initialize the MA Touch entity."""

        self._ma_config = entry.runtime_data.ma_config
        self._thermostat = entry.runtime_data.thermostat
        self._attr_unique_id = f"matouch_{format_mac(self._ma_config.mac_address)}"
        self._attr_device_info = DeviceInfo(
            name=f"MA Touch {format_mac(self._ma_config.mac_address)}",
            manufacturer=MANUFACTURER,
            model=DEVICE_MODEL,
            connections={(CONNECTION_BLUETOOTH, self._ma_config.mac_address)},
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added to hass."""

        self._thermostat.register_callback(MAEvent.CONNECTED, self._async_on_connected)
        self._thermostat.register_callback(MAEvent.STATUS_RECEIVED, self._async_on_status_updated)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""

        self._thermostat.unregister_callback(MAEvent.CONNECTED, self._async_on_connected)
       
    @callback
    async def _async_on_connected(self) -> None:
        """Handle connection to the thermostat."""

        device_registry = dr.async_get(self.hass)
        if device := device_registry.async_get_device(
            connections={(CONNECTION_BLUETOOTH, self._ma_config.mac_address)},
        ):
            device_registry.async_update_device(
                device.id,
                hw_version=self._thermostat._firmware_version,
                sw_version=self._thermostat._software_version,
            )

    @callback
    async def _async_on_disconnected(self) -> None:
        """Handle disconnection from the thermostat."""

        #self._attr_available = False
        #self.async_write_ha_state()

    @callback
    async def _async_on_status_updated(self, status: Status) -> None:
        """Handle updated status from the thermostat."""

        match status.operation_mode:
            case MAOperationMode.AUTO:
                self._attr_min_temp = status.min_cool_temperature
                self._attr_max_temp = status.max_heat_temperature
                self._attr_target_temperature = None
                self._attr_target_temperature_high = status.cool_setpoint
                self._attr_target_temperature_low = status.heat_setpoint
            case MAOperationMode.HEAT:
                self._attr_min_temp = status.min_heat_temperature
                self._attr_max_temp = status.max_heat_temperature
                self._attr_target_temperature = status.heat_setpoint
                self._attr_target_temperature_high = None
                self._attr_target_temperature_low = None
            case MAOperationMode.COOL | MAOperationMode.DRY:
                self._attr_min_temp = status.min_cool_temperature
                self._attr_max_temp = status.max_cool_temperature
                self._attr_target_temperature = status.cool_setpoint
                self._attr_target_temperature_high = None
                self._attr_target_temperature_low = None
            case _:
                self._attr_target_temperature = None
                self._attr_target_temperature_high = None
                self._attr_target_temperature_low = None

        self._attr_hvac_mode = MA_TO_HA_HVAC[status.operation_mode]
        self._attr_hvac_action = self._get_current_hvac_action()
        self._attr_current_temperature = status.room_temperature
        self._attr_fan_mode = MA_TO_HA_FAN[status.fan_mode]
        self._attr_swing_mode = SWING_ON if status.vane_mode is MAVaneMode.SWING else SWING_OFF

        self._attr_available = True
        
        self.async_write_ha_state()

    def _get_current_hvac_action(self) -> HVACAction:
        """Return the current hvac action."""

        if self._thermostat.status is None or self._thermostat.status.operation_mode is MAOperationMode.OFF:
            return HVACAction.OFF

        match self._thermostat.status.operation_mode:
            case MAOperationMode.AUTO:
                return HVACAction.HEATING if self._thermostat.status.room_temperature <= self._thermostat.status.heat_setpoint else HVACAction.COOLING if self._thermostat.status.room_temperature >= self._thermostat.status.cool_setpoint else HVACAction.IDLE
            case MAOperationMode.HEAT:
                return HVACAction.HEATING if self._thermostat.status.room_temperature <= self._thermostat.status.heat_setpoint else HVACAction.IDLE
            case MAOperationMode.COOL:
                return HVACAction.COOLING if self._thermostat.status.room_temperature >= self._thermostat.status.cool_setpoint else HVACAction.IDLE
            case MAOperationMode.DRY:
                return HVACAction.DRYING if self._thermostat.status.room_temperature >= self._thermostat.status.cool_setpoint else HVACAction.IDLE
            case _:
                return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""

        try:
            temperature: float | None    
            if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
                match self._attr_hvac_mode:
                    case HVACMode.HEAT:
                        async with self._thermostat:
                            await self._thermostat.async_set_heat_setpoint(temperature)
                            await self._thermostat.async_get_status()
                    case HVACMode.COOL | HVACMode.DRY:
                        async with self._thermostat:
                            await self._thermostat.async_set_cool_setpoint(temperature)
                            await self._thermostat.async_get_status()
                    case _:
                        raise ServiceValidationError("Target setpoint is ambiguous in this mode")
            if (temperature := kwargs.get(ATTR_TARGET_TEMP_LOW)) is not None:
                async with self._thermostat:
                    await self._thermostat.async_set_heat_setpoint(temperature)
                    await self._thermostat.async_get_status()
            if (temperature := kwargs.get(ATTR_TARGET_TEMP_HIGH)) is not None:
                async with self._thermostat:
                    await self._thermostat.async_set_cool_setpoint(temperature)
                    await self._thermostat.async_get_status()
        except MAException as ex:
            raise ServiceValidationError(f"Failed to set temperature: {ex}") from ex
        except ValueError as ex:
            raise ServiceValidationError("Invalid temperature") from ex
    
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""

        try:
            async with self._thermostat:
                await self._thermostat.async_set_operation_mode(HA_TO_MA_HVAC[hvac_mode])
                await self._thermostat.async_get_status()
        except MAException as ex:
            raise ServiceValidationError(f"Failed to set HVAC mode: {ex}") from ex

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""

        try:
            async with self._thermostat:
                await self._thermostat.async_set_fan_mode(HA_TO_MA_FAN[fan_mode])
                await self._thermostat.async_get_status()
        except MAException:
            raise ServiceValidationError(f"Failed to set fan mode: {ex}") from ex

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""

        try:
            async with self._thermostat:
                await self._thermostat.async_set_vane_mode(MAVaneMode.SWING if swing_mode == SWING_ON else MAVaneMode.AUTO)
                await self._thermostat.async_get_status()
        except MAException:
            raise ServiceValidationError(f"Failed to set swing mode: {ex}") from ex
   
    @property
    def available(self) -> bool:
        """Whether the entity is available."""

        return self._thermostat.status is not None and self._attr_available

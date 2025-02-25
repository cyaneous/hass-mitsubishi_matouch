"""Platform for Mitsubishi MA Touch climate entities."""

from typing import Any

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo, format_mac
from homeassistant.components.climate.const import SWING_ON, SWING_OFF
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .btmatouch.const import MA_MIN_TEMP, MA_MAX_TEMP, MAOperationMode, MAVaneMode
from .btmatouch.exceptions import MAException

from .coordinator import MACoordinator

from . import MAConfigEntry
from .const import (
    DEVICE_MODEL,
    DEVICE_MODEL_ID,
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

    coordinator = MACoordinator(hass, entry)

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [MAClimate(coordinator)],
    )

async def async_unload_entry(hass: HomeAssistant, entry: MAConfigEntry) -> bool:
    """Unload a config entry."""

    return True

class MAClimate(CoordinatorEntity[MACoordinator], ClimateEntity):
    """Climate entity to represent an MA Touch thermostat."""

    _attr_entity_has_name = True
    _attr_name = None

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

    _attr_hvac_mode: HVACMode | None = None
    _attr_hvac_action: HVACAction | None = None
    _attr_current_temperature: float | None = None
    _attr_target_temperature: float | None = None
    _attr_target_temperature_high: float | None = None
    _attr_target_temperature_low: float | None = None
    _attr_fan_mode: str | None = None
    _attr_swing_mode: str | None = None

    def __init__(self, coordinator: MACoordinator):
        """Initialize the MA Touch entity."""

        super().__init__(coordinator)

        self._ma_config = coordinator.config_entry.runtime_data.ma_config
        self._thermostat = coordinator.config_entry.runtime_data.thermostat
        self._attr_unique_id = f"matouch_{format_mac(self._ma_config.mac_address)}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, self._ma_config.mac_address)},
            name=f"MA Touch {format_mac(self._ma_config.mac_address)}",
            manufacturer=MANUFACTURER,
            model=DEVICE_MODEL,
            model_id=DEVICE_MODEL_ID,
            sw_version=self._thermostat.software_version,
            hw_version=self._thermostat.firmware_version,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        status = self.coordinator.data

        match status.operation_mode:
            case MAOperationMode.AUTO:
                self._attr_min_temp = status.min_auto_temperature
                self._attr_max_temp = status.max_auto_temperature
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

        super()._handle_coordinator_update()

    def _get_current_hvac_action(self) -> HVACAction:
        """Return the current hvac action."""

        status = self.coordinator.data

        if status is None or status.operation_mode is MAOperationMode.OFF:
            return HVACAction.OFF

        match status.operation_mode:
            case MAOperationMode.AUTO:
                return HVACAction.HEATING if status.room_temperature <= status.heat_setpoint else HVACAction.COOLING if status.room_temperature >= status.cool_setpoint else HVACAction.IDLE
            case MAOperationMode.HEAT:
                return HVACAction.HEATING if status.room_temperature <= status.heat_setpoint else HVACAction.IDLE
            case MAOperationMode.COOL:
                return HVACAction.COOLING if status.room_temperature >= status.cool_setpoint else HVACAction.IDLE
            case MAOperationMode.DRY:
                return HVACAction.DRYING if status.room_temperature >= status.cool_setpoint else HVACAction.IDLE
            case _:
                return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""

        status = self.coordinator.data

        try:
            if temperature := kwargs.get(ATTR_TEMPERATURE):
                match status.operation_mode:
                    case MAOperationMode.HEAT:
                        await self.coordinator.async_set_heat_setpoint(temperature)
                    case MAOperationMode.COOL | MAOperationMode.DRY:
                        await self.coordinator.async_set_cool_setpoint(temperature)
                    case _:
                        raise ServiceValidationError("Target setpoint is ambiguous in this mode")
            if temperature := kwargs.get(ATTR_TARGET_TEMP_LOW):
                await self.coordinator.async_set_heat_setpoint(temperature)
            if temperature := kwargs.get(ATTR_TARGET_TEMP_HIGH):
                await self.coordinator.async_set_cool_setpoint(temperature)
        except MAException as ex:
            raise ServiceValidationError(f"Failed to set temperature: {ex}") from ex
        except ValueError as ex:
            raise ServiceValidationError("Invalid temperature") from ex

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""

        try:
            await self.coordinator.async_set_operation_mode(HA_TO_MA_HVAC[hvac_mode])
        except MAException as ex:
            raise ServiceValidationError(f"Failed to set HVAC mode: {ex}") from ex

    async def async_set_fan_mode(self, fan_mode) -> None:
        """Set new target fan mode."""

        try:
            await self.coordinator.async_set_fan_mode(HA_TO_MA_FAN[fan_mode])
        except MAException as ex:
            raise ServiceValidationError(f"Failed to set fan mode: {ex}") from ex

    async def async_set_swing_mode(self, swing_mode) -> None:
        """Set new target swing operation."""

        try:
            vane_mode = MAVaneMode.SWING if swing_mode == SWING_ON else MAVaneMode.AUTO
            await self.coordinator.async_set_vane_mode(vane_mode)
        except MAException as ex:
            raise ServiceValidationError(f"Failed to set swing mode: {ex}") from ex

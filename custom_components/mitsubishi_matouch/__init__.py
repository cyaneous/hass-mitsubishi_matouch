"""Support for Mitsubishi MA Touch thermostats."""

from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .btmatouch.thermostat import Thermostat

from .models import MAConfigEntry, MAConfig, MAConfigEntryRuntimeData

PLATFORMS = [
    Platform.CLIMATE,
]

async def async_setup_entry(hass: HomeAssistant, config_entry: MAConfigEntry) -> bool:
    """Handle config entry setup."""

    mac_address: str = config_entry.unique_id
    pin: str = config_entry.data.get("pin")

    if TYPE_CHECKING:
        assert mac_address is not None
        assert pin is not None

    ma_config = MAConfig(
        mac_address=mac_address,
        pin=pin
    )

    device = bluetooth.async_ble_device_from_address(
        hass, mac_address.upper(), connectable=True
    )

    if device is None:
        raise ConfigEntryNotReady(f"MA Touch thermostat '{mac_address}' could not be found")

    thermostat = Thermostat(
        mac_address=mac_address,
        pin=int(pin, 16),
        ble_device=device
    )

    config_entry.runtime_data = MAConfigEntryRuntimeData(
        ma_config=ma_config,
        thermostat=thermostat
    )

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: MAConfigEntry) -> bool:
    """Handle config entry unload."""

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, config_entry: MAConfigEntry) -> None:
    """Handle config entry update."""

    await hass.config_entries.async_reload(config_entry.entry_id)

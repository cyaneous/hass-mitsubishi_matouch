"""Support for Mitsubishi MA Touch thermostats."""

import logging

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .btmatouch.thermostat import Thermostat

from .models import MAConfigEntry, MAConfig, MAConfigEntryRuntimeData

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.CLIMATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: MAConfigEntry) -> bool:
    """Handle config entry setup."""

    mac_address: str = entry.unique_id
    pin: str = entry.data.get("pin")

    if pin is None or len(pin) != 4:
        raise ConfigEntryNotReady(f"MA Touch thermostat '{mac_address}' is missing PIN configuration")

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

    config = MAConfig(
        mac_address=mac_address,
        pin=pin
    )

    entry.runtime_data = MAConfigEntryRuntimeData(
        config=config,
        thermostat=thermostat
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MAConfigEntry) -> bool:
    """Handle config entry unload."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: MAConfigEntry) -> None:
    """Handle config entry update."""

    await hass.config_entries.async_reload(entry.entry_id)

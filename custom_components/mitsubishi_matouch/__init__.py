"""Support for Mitsubishi MA Touch thermostats."""

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .btmatouch.thermostat import Thermostat
from .btmatouch.exceptions import MAException

from .models import MAConfig, MAConfigEntryData

PLATFORMS = [
    Platform.CLIMATE,
]

_LOGGER = logging.getLogger(__name__)

type MAConfigEntry = ConfigEntry[MAConfigEntryData]


async def async_setup_entry(hass: HomeAssistant, entry: MAConfigEntry) -> bool:
    """Handle config entry setup."""

    mac_address: str = entry.unique_id
    pin: str = entry.data.get("pin")

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

    entry.runtime_data = MAConfigEntryData(
        ma_config=ma_config,
        thermostat=thermostat
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_create_background_task(
        hass, _async_run_thermostat(hass, entry), entry.entry_id
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MAConfigEntry) -> bool:
    """Handle config entry unload."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: MAConfigEntry) -> None:
    """Handle config entry update."""

    await hass.config_entries.async_reload(entry.entry_id)


async def _async_run_thermostat(hass: HomeAssistant, entry: MAConfigEntry) -> None:
    """Run the thermostat update loop."""

    thermostat = entry.runtime_data.thermostat
    mac_address = entry.runtime_data.ma_config.mac_address
    scan_interval = entry.runtime_data.ma_config.scan_interval

    while True:
        try:
            async with thermostat:
                await thermostat.async_get_status()
        except MAException as ex:
            _LOGGER.error("[%s] Error updating MA Touch thermostat: %s", mac_address, ex)

        await asyncio.sleep(scan_interval)

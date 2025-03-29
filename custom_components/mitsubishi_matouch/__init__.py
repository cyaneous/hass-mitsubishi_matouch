"""Support for Mitsubishi MA Touch thermostats."""

import logging

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .models import MAConfigEntry, MAConfig, MAConfigEntryRuntimeData
from .coordinator import MACoordinator

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

    config = MAConfig(
        mac_address=mac_address,
        pin=pin
    )

    coordinator = MACoordinator(
        hass,
        config_entry=entry,
        pin=config.pin,
        scan_interval=config.scan_interval,
        ble_device=device
    )

    entry.runtime_data = MAConfigEntryRuntimeData(
        config=config,
        coordinator=coordinator
    )

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MAConfigEntry) -> bool:
    """Handle config entry unload."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: MAConfigEntry) -> None:
    """Handle config entry update."""

    await hass.config_entries.async_reload(entry.entry_id)

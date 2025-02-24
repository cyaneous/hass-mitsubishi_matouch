"""Data update coordinator for Mitsubishi MA Touch thermostats."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, ConfigEntryAuthFailed

from .btmatouch.thermostat import Status
from .btmatouch.exceptions import MAException, MAAuthException

from .models import MAConfigEntry

_LOGGER = logging.getLogger(__name__)

class MACoordinator(DataUpdateCoordinator):
    """Mitsubishi MA Touch data update coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: MAConfigEntry):
        """Initialize the coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=config_entry.runtime_data.ma_config.mac_address,
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=config_entry.runtime_data.ma_config.scan_interval),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True,
        )

        self._thermostat = config_entry.runtime_data.thermostat

    async def _async_setup(self) -> None:
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """

    async def _async_update_data(self) -> Status:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with self._thermostat:
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                return await self._thermostat.async_get_status()
        except MAAuthException as ex:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from ex
        except MAException as ex:
            raise UpdateFailed(f"Error communicating with API: {ex}") from ex
            # _LOGGER.error("[%s] Error updating MA Touch thermostat: %s", mac_address, ex)

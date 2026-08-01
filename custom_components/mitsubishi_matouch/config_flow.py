"""Config flow for the Mitsubishi MA Touch integration.

Architecture: one parent config entry (the integration) + one "thermostat" config
subentry per device. The parent flow scans for MA Touch (CT01MA*) devices with a
live progress spinner that auto-advances the moment any are found, and lets the
user add several at once (name + PIN each). Thermostats can be added/edited/removed
later via the subentry flow without disturbing the others.
"""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_PIN
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_PREFER_PROXY,
    DEFAULT_PREFER_PROXY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MA_TOUCH_BLUETOOTH_PREFIX,
    MA_TOUCH_NAME_MATCH,
    MA_TOUCH_RENAMED_NAME_PREFIX,
    MA_TOUCH_SERVICE_UUID,
    SUBENTRY_TYPE_THERMOSTAT,
)

# Auto-search: poll discovery this many times, this far apart, advancing as soon
# as anything is found (so a unit that needs a moment to advertise still shows up).
_DISCOVERY_ROUNDS = 30
_DISCOVERY_DELAY = 2.0


def _is_matouch(info: BluetoothServiceInfoBleak) -> bool:
    """Return whether an advertised device looks like an MA Touch controller.

    Matches the "CT01MA" model substring in factory names (for example,
    "M/R_CT01MAU_<machex>"). Since a controller's advertised name is configurable,
    also recognizes the observed MA Touch M/R_ name prefix paired with its 58:52:8A
    Bluetooth address block. The service UUID is GATT-only (not advertised), so it
    is only a secondary hint.
    """

    if MA_TOUCH_SERVICE_UUID in (info.service_uuids or []):
        return True

    name = (info.name or "").upper()
    if MA_TOUCH_NAME_MATCH in name:
        return True

    return (
        name.startswith(MA_TOUCH_RENAMED_NAME_PREFIX)
        and info.address.upper().startswith(MA_TOUCH_BLUETOOTH_PREFIX)
    )


def _valid_pin(pin: str) -> bool:
    """Return whether the PIN is 4 digits."""

    return pin.isdigit() and len(pin) == 4


def _device_options(devices: dict[str, BluetoothServiceInfoBleak]) -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=address, label=f"{(info.name or 'MA Touch')} ({address})")
        for address, info in devices.items()
    ]


async def _collect_matouch(hass, found: dict[str, BluetoothServiceInfoBleak], exclude: set[str]) -> None:
    """Poll discovery until at least one (new) MA Touch device is found, or timeout."""

    for _ in range(_DISCOVERY_ROUNDS):
        for info in async_discovered_service_info(hass, connectable=True):
            if info.address not in exclude and _is_matouch(info):
                found[info.address] = info
        if found:
            return
        await asyncio.sleep(_DISCOVERY_DELAY)


class MAConfigFlow(ConfigFlow, domain=DOMAIN):
    """Parent config flow for Mitsubishi MA Touch."""

    # Bump the MINOR version (not MAJOR) so async_migrate_entry runs on (a) pre-fork
    # cyaneous per-device entries and (b) early-fork parent entries created before any
    # version was declared — while keeping in-place DOWNGRADES allowed (HA only blocks
    # major-version downgrades with MIGRATION_ERROR). That keeps "revert via HACS" clean.
    # 3: heals the v0.14.0 promote bug (stray entry-level device link). 2: initial migration.
    MINOR_VERSION = 3

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}
        self._discover_task: asyncio.Task | None = None
        self._pending: list[str] = []
        self._collected: dict[str, dict[str, Any]] = {}

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Thermostats are added as subentries under the parent entry."""

        return {SUBENTRY_TYPE_THERMOSTAT: ThermostatSubentryFlowHandler}

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        """Handle a device discovered over Bluetooth (single-instance parent)."""

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if _is_matouch(discovery_info):
            self._discovered[discovery_info.address] = discovery_info
        self.context["title_placeholders"] = {"name": "Mitsubishi MA Touch"}
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Auto-search for thermostats with a live progress spinner."""

        await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        if self._discover_task is None:
            self._discover_task = self.hass.async_create_task(
                _collect_matouch(self.hass, self._discovered, set())
            )

        if not self._discover_task.done():
            return self.async_show_progress(
                step_id="user",
                progress_action="searching",
                progress_task=self._discover_task,
            )

        self._discover_task = None
        return self.async_show_progress_done(
            next_step_id="pick" if self._discovered else "retry"
        )

    async def async_step_retry(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Shown when no thermostats were found; submitting searches again."""

        if user_input is not None:
            self._discovered = {}
            return await self.async_step_user()
        return self.async_show_form(step_id="retry", data_schema=vol.Schema({}))

    async def async_step_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick which discovered thermostats to add."""

        if user_input is not None:
            self._pending = list(user_input[CONF_ADDRESS])
            self._collected = {}
            return await self.async_step_device()

        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=_device_options(self._discovered),
                            mode=SelectSelectorMode.LIST,
                            multiple=True,
                            sort=True,
                        )
                    ),
                }
            ),
        )

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Collect a name + PIN for each selected thermostat, one at a time."""

        errors: dict[str, str] = {}
        if user_input is not None:
            address = self._pending[0]
            pin = user_input[CONF_PIN]
            if not _valid_pin(pin):
                errors[CONF_PIN] = "invalid_pin"
            else:
                self._collected[address] = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_PIN: pin,
                    CONF_ADDRESS: address,
                }
                self._pending.pop(0)

        if not self._pending:
            return self.async_create_entry(
                title="Mitsubishi MA Touch",
                data={},
                subentries=[
                    ConfigSubentryData(
                        subentry_type=SUBENTRY_TYPE_THERMOSTAT,
                        title=info[CONF_NAME],
                        unique_id=address,
                        data=info,
                    )
                    for address, info in self._collected.items()
                ],
            )

        address = self._pending[0]
        info = self._discovered.get(address)
        default_name = (info.name if info else None) or f"MA Touch {address}"
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=default_name): str,
                    vol.Required(CONF_PIN): str,
                }
            ),
            description_placeholders={"device": f"{default_name} ({address})"},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""

        return MAOptionsFlow()


class ThermostatSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure a single thermostat subentry."""

    def __init__(self) -> None:
        """Initialize the subentry flow."""

        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add a thermostat: scan for new CT01MA devices, collect name + PIN.

        Re-scans on every entry to this step, so an empty result is retryable
        (submit to search again) rather than a dead end.
        """

        entry = self._get_entry()
        existing = {se.data.get(CONF_ADDRESS) for se in entry.subentries.values()}
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address not in existing and _is_matouch(info):
                self._discovered[info.address] = info

        errors: dict[str, str] = {}
        if user_input is not None and self._discovered:
            pin = user_input.get(CONF_PIN, "")
            if not _valid_pin(pin):
                errors[CONF_PIN] = "invalid_pin"
            else:
                address = user_input[CONF_ADDRESS]
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_PIN: pin,
                        CONF_ADDRESS: address,
                    },
                    unique_id=address,
                )

        if not self._discovered:
            # Retryable: an empty form whose submit re-runs this step (re-scans).
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors={"base": "no_devices_found"},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=_device_options(self._discovered),
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=True,
                        )
                    ),
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_PIN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Edit a thermostat's name / PIN."""

        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            pin = user_input[CONF_PIN]
            if not _valid_pin(pin):
                errors[CONF_PIN] = "invalid_pin"
            else:
                return self.async_update_and_abort(
                    entry,
                    subentry,
                    title=user_input[CONF_NAME],
                    data_updates={CONF_NAME: user_input[CONF_NAME], CONF_PIN: pin},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=subentry.data.get(CONF_NAME, "")): str,
                    vol.Required(CONF_PIN, default=subentry.data.get(CONF_PIN, "")): str,
                }
            ),
            errors=errors,
        )


class MAOptionsFlow(OptionsFlow):
    """Options flow for Mitsubishi MA Touch (applies to all thermostats)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the integration options."""

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PREFER_PROXY,
                        default=opts.get(CONF_PREFER_PROXY, DEFAULT_PREFER_PROXY),
                    ): bool,
                    vol.Optional(
                        "scan_interval", default=opts.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                    vol.Optional("log_polls", default=opts.get("log_polls", False)): bool,
                    vol.Optional(
                        "capture_raw_frames", default=opts.get("capture_raw_frames", False)
                    ): bool,
                }
            ),
        )

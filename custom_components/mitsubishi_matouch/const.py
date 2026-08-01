"""Constants for the Mitsubishi MA Touch integration."""

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
)

from .btmatouch.const import MAOperationMode, MAFanMode, MAVaneMode, MARightLeftMode
from .btmatouch.capabilities import (
    VANE_AUTO,
    VANE_SWING,
    VANE_POSITION_LABELS,
    RL_AUTO,
    RL_SWING,
    RL_POSITION_LABELS,
)

DOMAIN = "mitsubishi_matouch"

SUBENTRY_TYPE_THERMOSTAT = "thermostat"
# Factory-named units advertise as "M/R_CT01MAU_<machex>" (and
# "M/R_CT01MA_<machex>" on some), so match the model designation as a substring.
MA_TOUCH_NAME_MATCH = "CT01MA"
# A controller's advertised name is user-configurable. Observed MA Touch controllers
# retain the M/R_ prefix and use Mitsubishi's 58:52:8A Bluetooth address block, which
# provides a narrow, name-independent discovery hint for renamed controllers.
MA_TOUCH_RENAMED_NAME_PREFIX = "M/R_"
MA_TOUCH_BLUETOOTH_PREFIX = "58:52:8A:"
# Note: this is a GATT service, NOT advertised — kept only as a secondary hint.
MA_TOUCH_SERVICE_UUID = "0277df18-e796-11e6-bf01-fe55135034f3"

MANUFACTURER = "Mitsubishi Electric"
DEVICE_MODEL = "MA Touch"
DEVICE_MODEL_ID = "PAR-CT01MAU"

MA_TO_HA_HVAC: dict[MAOperationMode, HVACMode] = {
    MAOperationMode.OFF: HVACMode.OFF,
    MAOperationMode.AUTO: HVACMode.AUTO,
    MAOperationMode.HEAT: HVACMode.HEAT,
    MAOperationMode.COOL: HVACMode.COOL,
    MAOperationMode.DRY: HVACMode.DRY,
    MAOperationMode.FAN: HVACMode.FAN_ONLY,
}

HA_TO_MA_HVAC: dict[HVACMode, MAOperationMode] = {
    HVACMode.OFF: MAOperationMode.OFF,
    HVACMode.AUTO: MAOperationMode.AUTO,
    HVACMode.HEAT: MAOperationMode.HEAT,
    HVACMode.COOL: MAOperationMode.COOL,
    HVACMode.DRY: MAOperationMode.DRY,
    HVACMode.FAN_ONLY: MAOperationMode.FAN,
}

MA_TO_HA_FAN: dict[MAFanMode, str] = {
    MAFanMode.AUTO: FAN_AUTO,
    MAFanMode.HIGH: FAN_HIGH,
    MAFanMode.MEDIUM: FAN_MEDIUM,
    MAFanMode.LOW: FAN_LOW,
    MAFanMode.QUIET: "quiet",
}

HA_TO_MA_FAN: dict[str, MAFanMode] = {
    FAN_AUTO: MAFanMode.AUTO,
    FAN_HIGH: MAFanMode.HIGH,
    FAN_MEDIUM: MAFanMode.MEDIUM,
    FAN_LOW: MAFanMode.LOW,
    "quiet": MAFanMode.QUIET,
}

# --- Vane (vertical airflow) <-> HA swing_mode keys ----------------------------
# The vane has up to 5 fixed positions plus auto + swing, surfaced via the climate swing
# control (gated by the per-unit vane capability). The mapped strings are stable machine
# KEYS (capabilities.VANE_*); Home Assistant renders the display labels + per-position
# icons from the entity translations / icons.json. Wire ordering is AUTHORITATIVE from the
# decompiled SDK: wire 3 = FLAT (airflow level), 5 = DOWNWARD20, 2 = DOWNWARD60,
# 1 = DOWNWARD80, 0 = DOWNWARD100 (fully down). (GeminiMobileData WindDirection.toRequestValue
# / convertDirectionToVane.)
#
# READ is mapped by the WIRE VALUE (not the MAVaneMode member) because MAVaneMode.NONE
# and STEP_5 both equal 0 — an enum lookup of 0 yields NONE, so a value table avoids
# that alias. SET maps the HA key to the right MAVaneMode member.
MA_VANE_VALUE_TO_HA: dict[int, str] = {
    int(MAVaneMode.AUTO): VANE_AUTO,                 # 6
    int(MAVaneMode.STEP_1): VANE_POSITION_LABELS[0], # 3 -> flat
    int(MAVaneMode.STEP_2): VANE_POSITION_LABELS[1], # 5 -> down_20
    int(MAVaneMode.STEP_3): VANE_POSITION_LABELS[2], # 2 -> down_60
    int(MAVaneMode.STEP_4): VANE_POSITION_LABELS[3], # 1 -> down_80
    int(MAVaneMode.STEP_5): VANE_POSITION_LABELS[4], # 0 -> down_100
    int(MAVaneMode.SWING): VANE_SWING,               # 7
}
HA_TO_MA_VANE: dict[str, MAVaneMode] = {
    VANE_AUTO: MAVaneMode.AUTO,
    VANE_POSITION_LABELS[0]: MAVaneMode.STEP_1,
    VANE_POSITION_LABELS[1]: MAVaneMode.STEP_2,
    VANE_POSITION_LABELS[2]: MAVaneMode.STEP_3,
    VANE_POSITION_LABELS[3]: MAVaneMode.STEP_4,
    VANE_POSITION_LABELS[4]: MAVaneMode.STEP_5,
    VANE_SWING: MAVaneMode.SWING,
}

# --- Horizontal (left/right) vane <-> HA swing_horizontal_mode keys ------------
# right_left is bits 4-6 of the status running-state byte (SDK GeminiMobileData.RightLeft /
# MARightLeftMode), surfaced via the native SWING_HORIZONTAL_MODE control (HA >= 2024.12),
# gated on the per-unit right_left capability. Mapped strings are capabilities.RL_* KEYS;
# labels + icons come from translations / icons.json. READ maps by wire VALUE; SET maps the
# HA key back to the MARightLeftMode member.
MA_RL_VALUE_TO_HA: dict[int, str] = {
    int(MARightLeftMode.AUTO): RL_AUTO,                        # 2
    int(MARightLeftMode.SWING): RL_SWING,                      # 1
    int(MARightLeftMode.LEFT): RL_POSITION_LABELS[0],          # 3 -> rl_left
    int(MARightLeftMode.LEFT_CENTER): RL_POSITION_LABELS[1],   # 4 -> rl_left_center
    int(MARightLeftMode.CENTER): RL_POSITION_LABELS[2],        # 0 -> rl_center
    int(MARightLeftMode.RIGHT_CENTER): RL_POSITION_LABELS[3],  # 5 -> rl_right_center
    int(MARightLeftMode.RIGHT): RL_POSITION_LABELS[4],         # 6 -> rl_right
}
HA_TO_MA_RL: dict[str, MARightLeftMode] = {
    RL_AUTO: MARightLeftMode.AUTO,
    RL_SWING: MARightLeftMode.SWING,
    RL_POSITION_LABELS[0]: MARightLeftMode.LEFT,
    RL_POSITION_LABELS[1]: MARightLeftMode.LEFT_CENTER,
    RL_POSITION_LABELS[2]: MARightLeftMode.CENTER,
    RL_POSITION_LABELS[3]: MARightLeftMode.RIGHT_CENTER,
    RL_POSITION_LABELS[4]: MARightLeftMode.RIGHT,
}

# --- Running state (unit_state) ------------------------------------------------
# unit_state is the low nibble of the status frame's running-state byte (SDK
# GeminiMobileData.UnitState wire values), decoded in models.Status. IMPORTANT — verified
# live on our slim/RAC units (2026-07-03, raw-frame diff across on/off/cooling): these
# units keep unit_state at NORMAL(0) the WHOLE time they are actively conditioning; the
# explicit COOL(5)/HEAT(6) values are City-Multi-only and never appear here. So NORMAL does
# NOT mean idle — it means "operating normally in the set mode." unit_state only leaves 0
# for the special outdoor states below, matching the MELRemo app (its status icon is
# power+mode; unit_state only drives the standby/defrost labels and the wait-multi blink).
# Consequently hvac_action derives the base action from the MODE when on (see
# climate.hvac_action) and uses these values only as overrides.
MA_UNIT_STATE_NORMAL = 0            # operating normally (actively conditioning per the mode)
MA_UNIT_STATE_STANDBY_HEAT = 1      # heat pre-warm  -> PREHEATING
MA_UNIT_STATE_DEFROST = 2           # defrost cycle  -> DEFROSTING
MA_UNIT_STATE_WAIT_MULTI = 4        # on but shared outdoor unit is serving another head -> IDLE
MA_UNIT_STATE_COOL = 5              # explicit cool (City-Multi; unused on slim)
MA_UNIT_STATE_HEAT = 6              # explicit heat (City-Multi; unused on slim)
MA_UNIT_STATE_REQUEST_COMP_OFF = 7  # compressor commanded off / satisfied -> IDLE

# Stable snake_case names for the raw unit_state, surfaced as a climate extra-state
# attribute for automations/history. These strings are historical — keep them stable.
MA_UNIT_STATE_NAMES: dict[int, str] = {
    MA_UNIT_STATE_NORMAL: "normal",
    MA_UNIT_STATE_STANDBY_HEAT: "standby_heat",
    MA_UNIT_STATE_DEFROST: "defrost",
    MA_UNIT_STATE_WAIT_MULTI: "wait_multi",
    MA_UNIT_STATE_COOL: "cool",
    MA_UNIT_STATE_HEAT: "heat",
    MA_UNIT_STATE_REQUEST_COMP_OFF: "request_comp_off",
}

# HOLD is surfaced as a climate preset (only on units whose capability blob advertises
# holdfunc). PRESET_NONE is HA's "no preset".
PRESET_HOLD = "hold"

DEFAULT_SCAN_INTERVAL = 10 # seconds; cheap now that the connection is persistent (keepalive holds it)

# When balancing across proxies, skip proxies that hear the device weaker than
# this (dBm), unless no stronger proxy can reach it.
PROXY_RSSI_FLOOR = -90

# Integration-wide option: prefer any REMOTE Bluetooth proxy (ESP32/ESPHome, Shelly,
# future tech — anything that isn't the host's own adapter) over the HOST's built-in /
# HCI Bluetooth radio for connections, REGARDLESS of RSSI — i.e. only fall back to the
# local adapter when no proxy can reach the device at all. Default on: the host radio
# is oversubscribed by many persistent connections, can't be near every unit, and is
# subject to WiFi/BT coexistence + USB3 interference + kernel-driver breakage — so a
# proxy is the better path in essentially every scenario except outright unavailability.
# "Remote" is detected negatively (not one of the host's own Bluetooth adapter MACs, from
# the habluetooth manager), so no per-proxy-type knowledge is hard-coded. Key kept as
# "prefer_proxy" for compat.
CONF_PREFER_PROXY = "prefer_proxy"
DEFAULT_PREFER_PROXY = True

# Dispatcher signal (namespaced per entry) fired when a thermostat subentry is
# added at runtime so the platforms create its entities without a parent reload.
SIGNAL_NEW_THERMOSTAT = "mitsubishi_matouch_new_thermostat"

# Dispatcher signal (namespaced per entry, payload = subentry_id) fired once when a
# unit's capability blob first loads. Capability-gated entities that only make sense on
# units with the feature (the Vane select, the Hold switch) are created in response, so
# they appear only where supported rather than as permanently-unavailable phantoms.
SIGNAL_CAPS_LOADED = "mitsubishi_matouch_caps_loaded"

# Active-rebalance tuning. Rebalance is event-driven (proxy online/offline) with a
# slow periodic backstop; a debouncer coalesces bursts and serializes runs.
REBALANCE_INTERVAL = 600       # slow periodic backstop (seconds)
REBALANCE_COOLDOWN = 1800      # min seconds before re-bouncing the same device
REBALANCE_DEBOUNCE = 5.0       # coalesce a burst of proxy events into one run
REBALANCE_STEP_DELAY = 6.0     # let a bounced device reconnect before re-evaluating

# Per-coordinator exponential backoff cap (seconds) on repeated connect/link
# failures, so an unreachable unit / saturated proxy is not hammered every poll.
MAX_BACKOFF_INTERVAL = 120

# How often to re-evaluate a failing unit's availability. HA's DataUpdateCoordinator
# only fires entity updates on a success or the FIRST failure of a streak, so a
# time-based "stale" grey-out would otherwise never be re-checked during a sustained
# outage (the card stays online showing stale data). A timer nudges listeners while a
# unit is failing so it greys on schedule. The same tick re-evaluates the
# "wedged" (discoverable-but-won't-connect) Repairs notice below.
AVAILABILITY_TICK_INTERVAL = 15

# How long a unit may stay DISCOVERABLE (a proxy sees it advertising) while EVERY
# connect/poll fails before we raise a Repairs notice that its radio is likely wedged
# and needs a power cycle. Set well above the normal periodic drop-and-reconnect blip
# (and above the exponential backoff) so an ordinary recoverable hiccup never trips it;
# only a genuinely stuck unit (advertising yet unjoinable for this long) does.
WEDGED_UNIT_THRESHOLD = 600

# How long the device must keep answering operation/settings requests with
# ERROR_FROM_DEVICE (result 0x09) before we raise the "thermostat fault" Repairs notice.
# The device is connected and authenticates (so this isn't a link/wedge issue) but
# rejects everything — a unit stuck on an error/startup screen. Long enough that a user
# briefly in the on-device menus (which also returns 0x09) doesn't trip it; it clears the
# moment a poll succeeds.
DEVICE_FAULT_THRESHOLD = 180

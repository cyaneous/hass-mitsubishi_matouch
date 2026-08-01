# Changelog

This is a hardened fork of [cyaneous/hass-mitsubishi_matouch](https://github.com/cyaneous/hass-mitsubishi_matouch),
focused on running several MA Touch (PAR-CT01MAU) thermostats reliably over ESP32
Bluetooth proxies, 24/7.

## 0.14.41

- **Discover renamed MA Touch controllers.** The controller advertises only its
  user-configurable local name (not manufacturer data or its GATT service UUID).
  Discovery now triggers for the observed MA Touch `M/R_` name prefix and
  accepts candidates only when they also use the `58:52:8A` Bluetooth address
  block, while retaining the factory-name (`CT01MA`) match.

## 0.14.40

- **Surface multi-split mode conflict.** On a multi-split the shared outdoor unit runs
  one mode at a time, so a head requesting the opposite mode is parked and waits.
  `hvac_mode` already reflects the unit's reported mode, and a new **`mode_conflict`**
  climate attribute (`true` when the device reports `WAIT_MULTI`) flags that the requested
  mode can't run right now — the same signal the MELRemo app shows by flashing the mode
  icon. Verified live by inducing a heat-vs-cool conflict on a unit.

## 0.14.39

- **`hvac_action` follows the running mode when the unit is on.** On these slim/RAC units
  the device's running-state field stays `NORMAL` the whole time a unit is actively
  conditioning (confirmed live via a raw-frame on/off/cooling diff — the `COOL`/`HEAT`
  states are City-Multi-only), so 0.14.38's "read the running state → IDLE" made the card
  read *idle* whenever on. The action now derives from the running **mode** when on
  (cool → cooling, heat → heating, dry → drying, fan → fan), using the running-state field
  only as an override for the special states it actually reports (defrost, heat pre-warm,
  wait-for-outdoor-unit). The raw state stays available as a `unit_state` attribute.

## 0.14.38

- **`hvac_action` reads the device's real running state** instead of inferring it from
  room-vs-setpoint. The **horizontal (left/right) vane** is exposed via Home Assistant's
  native `swing_horizontal_mode` control (capability-gated). Vane positions get proper
  capitalized labels and **per-position icons** via entity translations + `icons.json`.

## 0.14.34 – 0.14.37

- **Prefer remote Bluetooth proxies over the host's built-in adapter** — new option,
  **on by default.** Routes every connection through a remote proxy (ESP32/ESPHome,
  Shelly, …) whenever one can reach the thermostat, even if the host's own adapter reports
  a stronger signal; the host radio is used only as a last resort. The host adapter is
  oversubscribed by persistent connections and prone to Wi-Fi/Bluetooth coexistence, USB-3
  interference, and driver breakage, so a proxy is the better path in nearly every case.
  This range also **absorbs the endemic ~43-minute device-side BLE link recycle** (the
  availability grace + stale-floor are tuned so the card rides through the recycle instead
  of flickering unavailable ~hourly), reads the host's own adapters via the `habluetooth`
  manager API, and fixes a doubled MAC in the `active_proxy` sensor.

## 0.14.33

- **Vane back in the climate card as the swing control.** Re-exposes the vertical vane as
  the climate `swing_mode` control (0.14.27 had moved it to a select entity).

## 0.14.32

- **Send the full 16-bit outbound checksum.** The outbound frame checksum was truncated to
  8 bits, so any frame whose byte-sum exceeded 255 got a wrong checksum and was **silently
  dropped by the device** (which looked like an auth/response timeout). Fixed to the full
  16-bit additive sum, matching the already-correct inbound path; regression-locked in
  `tests/test_checksum.py`.

## 0.14.31

- **Cut recorder flooding and BLE log-noise.** Reduced per-poll churn into the recorder and
  downgraded the noisy "unsolicited / late frame" messages (common on weak links) to debug,
  so 24/7 operation stays quiet.

## 0.14.28 – 0.14.30

- **Device-fault detection.** A unit that connects and authenticates but rejects every
  operation/settings command with a device error (result `0x09` — e.g. stuck on an `E4`
  startup screen) now raises a **`device_fault` Repairs** notice and a per-unit **Fault**
  binary_sensor. Detection is generic (any non-transient device-error result, not just
  `0x09`/`E4`), fleet-health-scoped so a user briefly in the on-device menus can't trip it,
  and clears the moment the unit operates normally. Includes a decoder for the device's
  logged `g0` fault records (check code, source address, timestamp), regression-tested.

## 0.14.23 – 0.14.27

- **Capabilities surfaced and controls wired.** The per-unit capability blob (parsed in
  0.14.22) now **gates** the exposed HVAC/fan/swing modes and vane positions to what each
  unit actually supports, is summarized in a single per-unit **Capabilities** diagnostic
  sensor, and drives the **Hold** and **vane** controls. Vane swing positions carry
  human-readable labels (horizontal / down N% / fully down). (Hold and vane iterated
  through preset/select/switch forms across this range before settling.)

## 0.14.17 – 0.14.22

- **Device-info / capability fetch — reverse-engineered and validated live.** Cracked the
  session-3 `begin → data → end` sequence that reads a unit's capability blob from IDLE
  with the ordinary user PIN, fixing the session ordering (`begin-0 → end-0 → begin-3`, the
  credential tier, and the inbound frame-length bound for the ~85-byte blob) and correcting
  `0x02` to mean **RESTART_JOB**, not a bad PIN. The blob is parsed into structured per-unit
  capabilities (connect type, supported modes, fan steps, vane / louver / vent / left-right /
  Move-Eye, temperature unit + step, hold, and the indoor-unit list). Added a
  `run_idle_sequence` debug harness for cracking session lifecycles safely off the poll path.

## 0.14.16

- **RE: on-demand device-info / capability fetch (`fetch_device_info` service).** The
  device-info command is a data frame (`0x0005`) that only works **inside a
  session_type-3 begin/data/end sequence** (RE'd from the SDK; the session type rides in
  a begin-session frame, not the data frame — which is why the earlier standalone
  `0x0003` attempt was rejected). `async_get_device_info()` now runs that full sequence
  using the stored PIN, and a new on-demand `fetch_device_info` service exposes it for a
  single unit. **On-demand only — never the login/poll path**, so a failure fails just
  that one call (at most one reconnect) and cannot loop. Returns the raw ~76-77-byte
  capability blob, to be parsed into per-unit capabilities next.

## 0.14.15

- **Add a safe, on-demand `send_raw_request` debug service (RE tooling).** Sends ONE
  arbitrary BLE request to a single thermostat (by MAC) and returns the raw response,
  with no validation, **off the login/poll path** — so a malformed request fails only
  that one call (at most one reconnect) and structurally cannot loop the way the
  v0.14.12 login-path fetch did. This is the foundation for cracking new-command
  framings (device-info/capability, fault history, energy) safely, one isolated shot at
  a time against one unit. No automatic use; nothing on the normal connection path
  changed.

## 0.14.14

- **Remove the HOLD switch.** Hardware validation (Theater) showed it's a no-op on these
  ducted units — the command is ACKed but changes nothing — so it was a dead control.
  Removed the switch platform. The control-frame protocol layer (louver/vent/left-right/
  Move-Eye/hold encoders + tests) stays dormant in the library for units that actually
  support those axes, to be exposed later only behind capability detection.

## 0.14.13

- **HOTFIX: revert the v0.14.12 device-info fetch — it took all units offline.** Calling
  `async_get_device_info()` during login made the device reply to the `0x0003` get-data
  with a 2-byte **runt** frame that desynced the frame assembler, so every subsequent
  status poll failed and **all thermostats went `unavailable`**. The get-data request
  framing is wrong and the receive buffer doesn't recover from a runt. The fetch is no
  longer called on the login path (the method is left dormant). Units recover on the next
  connect after deploying this. Capability detection will be retried only after the
  request framing and runt-recovery are fixed and validated off the live fleet.

## 0.14.12

- **RE groundwork: fetch the device-info / capability blob.** Added
  `Thermostat.async_get_device_info()` — the `e(3) a(0,0)` get-data request
  (message_type `0x0003` sent as GET-DATA, no PIN) that the MELRemo SDK uses to read a
  unit's capabilities (supported fan steps, vane, louver, vent, right/left, Move-Eye,
  hold, temp unit/step, model class). It's fetched at login (best-effort; can't break
  the connection) and the raw response is surfaced in **Download Diagnostics**
  (`device_info_hex`) so the 76-byte capability layout is parsed from real bytes rather
  than guessed. No user-facing change yet; capability-based gating of controls/modes
  follows once the response is confirmed.

## 0.14.11

- **New: HOLD switch — the first MELRemo-derived control axis.** Each thermostat gets a
  **Hold** switch (keep the current setpoint / suspend the schedule), driven through the
  extended control frame. It's optimistic with the same command-confirm + revert as the
  other controls, and greys out when the unit is unreachable. The remaining axes
  (vent / louver / left-right vane / Move-Eye) share the same protocol layer and follow
  once validated on hardware and capability-gated. HOLD is the first to ship because the
  device reports it back in the status frame, so it can be read, confirmed, and reverted.

## 0.14.10

- **Fix: tolerate the `0xFFFF` "not set" temperature sentinel.** The device sends
  `0xFFFF` for a setpoint/limit a given unit or mode doesn't use; decoding it did
  `float("ffff")` → ValueError, which failed the whole status parse and dropped the unit
  offline. It now decodes to `None` and every consumer guards it. Latent today but a
  real crash for some configs.
- **Internal (RE groundwork): capture the login / begin-session responses** (`0x0003`
  device-info and `0x0401`) into **Download Diagnostics**. These were discarded;
  surfacing the raw bytes lets the device-info / capability frame layout be reverse-
  engineered from real hardware before a parser is written — the first step toward
  capability detection (only exposing controls a unit supports), model/firmware info,
  and the other MELRemo-derived features. No user-facing change yet.

## 0.14.9

- **Converge temperature handling on the MELRemo app as the single source of truth.**
  The setpoint conversion previously used a separately-maintained CN105-derived table.
  Decompiling MELRemo v4.2.2 showed it agreed with the controller everywhere **except
  88 °F**, where the CN105 table mapped to 30.5 °C but the real remote uses **31.0 °C**
  — so setting max temp commanded a half-degree low. Setpoint and room/current temp now
  share one `_C_TO_F` table (and one `_F_TO_C` inverse) taken verbatim from MELRemo, so
  they cannot drift apart again, and the old second table is gone. Net behavior change:
  88 °F now commands 31.0 °C (was 30.5); 61–87 °F unchanged; room temp already corrected
  in 0.14.8. °C systems unaffected (passthrough).

## 0.14.8

- **Fix room temperature again — use the controller's lookup table, not truncation.**
  0.14.7 replaced round-half-up with truncation; reverse-engineering the official
  **MELRemo app (v4.2.2)** proved the controller converts BOTH setpoint and room temp
  through one nonlinear lookup table, and room temp is no exception. Truncation only
  matched in the 20–25 °C band (where the table happens to equal `int(c*9/5+32)`); it
  read **1 °F low below 20 °C and at/above 25.5 °C** (2 °F low at 30.5 °C). Room temp
  now uses the full 0–40 °C controller table (`_ROOM_C_TO_F`), which equals the setpoint
  table in the overlap and matches the physical display at every value. °C systems are
  unaffected (passthrough). Locked with tests incl. the previously-wrong points.

## 0.14.7

- **Fix room (current) temperature reading ~1°F high.** `current_temperature` was
  converted from the device's native °C with a round-**half-up** linear formula
  (`int(c*9/5+32+0.5)`), but the physical controller **truncates** the conversion (it
  drops the fraction; it does not round to nearest). In the common comfort band
  (~70-73°F) that made the HA card read **1°F above the wall display** — e.g. a sensor
  at 22.5°C (=72.5°F) showed **73** on the card but **72** on the thermostat, while
  23.0°C matched at 73. This was a *separate* path from the v0.13.3 setpoint fix
  (setpoints already used the Mitsubishi table and were correct). Room temp now
  truncates to match the controller exactly — **verified live against every unit**
  (decoded 0.5°C sensor value vs the physical wall display: 21.0→69, 22.0→71,
  22.5→72, 23.0→73). **°C systems stay exact:** the fix lives only in the °F branch;
  °C mode passes the device's native 0.5°C reading straight through — no conversion, so
  no rounding rule that could diverge from the controller.

## 0.14.6

- **Repairs notice for a wedged thermostat ("reachable but won't connect").** A unit
  can get into a state where its BLE radio keeps advertising (proxies see it, it shows
  multiple connection paths) but every connect/poll fails — so it goes `unavailable`
  and silently stays there for hours until someone notices and power-cycles it. The
  integration can't reset the unit's radio, but it can now *tell you*: when a unit is
  discoverable yet unjoinable for >10 min **while the rest of the fleet is healthy**, a
  Home Assistant *Repairs* issue is raised naming the unit and recommending a power
  cycle. It clears automatically the moment the unit reconnects. The detection is
  carefully scoped so it never fires for the benign cases — an offline/out-of-range
  unit (not discoverable), a wrong PIN or rejected command (the device answered, so the
  link works), or an ordinary periodic drop that recovers well under the threshold. The
  fleet-health gate keeps a global proxy outage from mis-blaming a single thermostat.

## 0.14.5

- **Fix: units still wouldn't grey on a sustained outage (follow-up to 0.14.4).** The
  bounded poll and the `is_stale` backstop were both working, but HA's
  `DataUpdateCoordinator` only notifies entities on a *success* or the *first* failure
  of a streak — so a card's availability was evaluated once at the start of the outage
  (while `is_stale` was not yet true) and **never re-checked**, leaving it "online" with
  stale data. (A unit only greyed if something else happened to nudge it — e.g. a
  setpoint-change revert.) Added a periodic availability tick that re-evaluates a
  *failing* unit every 15 s, so it greys within ~45–60 s of a real outage regardless of
  HA's listener behavior. No-op when healthy.

## 0.14.4

- **Fix: a unit could stay "online" through a proxy outage (and was slow to grey
  otherwise).** The per-poll timeout covered only the *connect* step, so a status read
  on a stale-but-"connected" link (proxy yanked, TCP not yet detected dead) could hang
  with no deadline — freezing the consecutive-failure counter so the card never went
  unavailable, and any optimistic setpoint change persisted indefinitely. Now:
  - the **entire** poll (connect + control writes + status read) runs under one
    timeout, so a hung step fails the poll and drops the link to reconnect;
  - availability has a **wall-clock staleness backstop** (no successful poll in several
    cadences ⇒ unavailable) that a frozen counter can't defeat;
  - a timed-out poll drops the stale link instead of trusting `is_connected`.

  A real outage is now detected in tens of seconds instead of minutes-or-never;
  recovery when the proxy returns is unchanged (fast).

## 0.14.3

- **Fix reload leaving every unit unavailable.** Setup blocked on a sequential
  per-thermostat BLE connect + firmware read (`async_config_entry_first_refresh`). On a
  **Reload**, the previous links are torn down first, so an immediate reconnect could
  hang and the GATT read got cancelled — and because it was the blocking first refresh,
  that cancelled the **whole** config entry with no retry, leaving all thermostats
  unavailable until a full restart. Setup now completes immediately and runs each unit's
  first poll in the background; a slow/flaky unit retries on its own backoff without
  taking down its siblings or the entry. (Startup was never affected — only reload.)

## 0.14.2

- **Fix raw translation placeholder in the config flow.** The "already configured"
  abort messages referenced Home Assistant's core string via
  `[%key:common::config_flow::abort::already_configured_device%]`, which only resolves
  for core integrations — so a custom install leaked the literal placeholder text into
  the dialog. Replaced with plain messages (parent flow points you to "Add thermostat"
  on the existing entry; subentry flow says the thermostat is already added).

## 0.14.1

- **Fix migration duplicate-device (regression in 0.14.0).** When a pre-fork entry
  was *promoted* in place to become the parent, its device kept a stray entry-level
  link alongside the new subentry link, so it showed up twice — once under its
  thermostat and once under "Devices that don't belong to a sub-entry." The promote
  path now drops that stray link (matching Home Assistant's own
  `openai_conversation` migration). Instances already migrated by 0.14.0 **self-heal**
  on upgrade (a one-time pass removes the stray link — no re-pairing needed).

## 0.14.0

- **Upgrade migration from the upstream (cyaneous) integration.** The original
  integration created one config entry per thermostat; this fork uses a single
  parent entry with a subentry per thermostat. Upgrading in place previously left
  the old pairings stranded and could create duplicate devices. A config-entry
  migration (minor version → 2, so reverting stays clean) now **adopts existing
  pairings**: it folds each old
  per-thermostat entry into the parent as a subentry and re-homes the existing
  device + climate entity, so **entity IDs and history are preserved** (no
  re-pairing, no duplicates). Early-fork parent entries are version-bumped in place
  (no structural change). The new diagnostic sensors appear fresh (expected).

## 0.13.9

- **Response checksum validation.** Every reply now has its trailing checksum
  verified (`sum(all bytes before the 2-byte checksum)` as a 16-bit little-endian
  value — confirmed against raw frames captured live from all five units). A
  mismatch is treated as a corrupt frame and retried, instead of being trusted.
  This eliminates rare **spurious "incorrect PIN"** events (a reply corrupted in
  transit whose result byte happened to read `0x02` was being misread as a wrong
  PIN) and guards against silently-corrupted temperature/mode data. Wire spec is
  regression-locked in `tests/test_checksum.py`.

## 0.13.4 – 0.13.8

- **Command confirmation.** Setpoint/mode/fan changes apply optimistically, then
  re-read; if the device rejects or the link drops, the entity reverts to actual
  state and surfaces a clear error — so the card never shows a change that didn't
  take.
- **Availability grace.** A single failed poll no longer flips the card to
  "unavailable"; it takes a short streak, which rides out one-off BLE hiccups.
- **Invalid-PIN repair.** A genuinely wrong PIN now raises a Home Assistant
  *Repairs* issue pointing at Reconfigure, and only after **3 consecutive** real
  rejections — connectivity blips can't false-trigger it.

## 0.13.3

- **Fahrenheit fix (upstream issue #4).** The device is Celsius-native (0.5°C steps)
  and Mitsubishi's °F display uses a non-linear lookup table, so reporting °C and
  letting HA convert produced a ~1°F off-by-one vs the physical controller. The
  climate entity now presents **Fahrenheit natively** (when HA's unit system is °F)
  using Mitsubishi's exact "standard" table, so HA does no conversion and the card
  matches the controller. Celsius systems are unchanged (exact passthrough).
  Conversion lives in `temperature.py`; round-trips are covered by `tests/`.
  - **Upgrade note for °F users:** the entity's reported unit changes from °C to °F,
    so `current_temperature` history shows a one-time discontinuity and HA may raise
    a "units changed" repair (resolvable via Developer Tools → Statistics). °C users
    are unaffected.
  - Known limitation: in °F mode the settable range matches the controller's °F
    table (61–88 °F = 16.0–30.5 °C); 31.0 °C is only reachable in °C mode.
- Config flow now **auto-searches** with a live progress spinner that advances as
  soon as a unit appears, instead of a dead-end "no devices found" abort.
- Resilience hardening: per-device exponential backoff with jitter on connect/link
  failures, reachability-aware proxy rebalancing (single-flight + debounced),
  immediate recovery when a proxy returns, and assorted concurrency fixes.

## 0.7.0 – 0.13.x (fork additions vs upstream 0.6.x)

- **Persistent BLE connections** with a 10s keepalive read that defeats the device's
  ~16s idle disconnect (per-poll cost drops to a single status round-trip).
- **ESP32 Bluetooth-proxy load balancing** across multiple proxies (least-loaded
  reachable proxy per device), so 4–5 thermostats share the radios evenly.
- **Telemetry** for R&D: a `mitsubishi_matouch.get_telemetry` service (response data),
  diagnostic sensors (uptime, reconnects, latency, active proxy, signal), Download
  Diagnostics, and an optional JSONL log. Raw-frame capture is opt-in (default off)
  to stay sustainable for 24/7 operation.
- **Config subentries:** one parent entry plus a removable "thermostat" subentry per
  device — scan-and-multi-select to add several at once, add/remove later without
  resetting the others.
- Pull-model climate entity, address-first setup (tolerates a unit briefly offline),
  and numerous reliability/QA fixes.

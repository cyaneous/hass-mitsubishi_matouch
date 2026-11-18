# Mitsubishi MA Touch for Home Assistant

[![hacs][hacs-badge]][hacs]
[![GitHub Release][release-badge]][releases]

A Home Assistant integration for **Mitsubishi MA Touch** wired thermostat
controllers (**PAR-CT01MAU**, and the **TAR-CT01MAU** sold by Trane) over
**Bluetooth LE**. It is fully local: no Kumo Cloud, no MELRemo app and no internet.
It runs several thermostats at once through ESP32 Bluetooth proxies, with persistent
connections and automatic recovery.

It is developed and run against five units (4× `PAR-CT01MAU` and 1× `PAR-CT01MA`)
on two ESP32 proxies.

Features:

- 🌡️ **Climate control** — HVAC mode (off / auto / heat / cool / dry / fan-only),
  heat and cool setpoints (including the auto-mode range), fan speed
  (auto / low / medium / high / quiet) and vane swing.
- 🔗 **Persistent BLE connections** — a keepalive holds the link open, so each poll
  is one status read instead of a reconnect and login.
- 📡 **Multi-proxy load balancing** — connections are spread across your Bluetooth
  proxies and rebalanced as proxies come and go.
- 🩺 **Diagnostic telemetry** — per-thermostat connection uptime, reconnects,
  latency, serving proxy and RSSI, plus a service that exports raw event data.
- ➕ **Several thermostats in one entry** — add a batch at once, then add or remove
  single thermostats without disturbing the others.
- 🇺🇸 **Fahrenheit that matches the controller** — uses Mitsubishi's °F lookup table.

<p align="center">
  <img src="images/thermostat-card.png" alt="Home Assistant thermostat card for a Living Area MA Touch unit, shown in Fahrenheit" width="330">
</p>

<p align="center"><sub>The Home Assistant thermostat card for one MA Touch unit.</sub></p>

## Requirements

- **Home Assistant 2025.3 or newer.** The integration uses config subentries (one
  parent entry with a "thermostat" subentry per device), which 2025.3 introduced.
- **A Bluetooth connection to your thermostats**: ESP32 Bluetooth proxies (ESPHome
  `bluetooth_proxy` in active mode), or a Bluetooth adapter on the Home Assistant
  host for thermostats within its range. See [Before you start](#before-you-start).
- **Each thermostat's PIN**, shown on the controller under **Settings → Bluetooth**.

## Supported devices

| Model | Status |
|---|---|
| **PAR-CT01MAU** | ✅ Verified (4 units) |
| **PAR-CT01MA** | ✅ Verified (1 unit) — a slightly longer status frame; the fields the integration uses decode identically |
| **TAR-CT01MAU** | ✅ Verified by a user — the PAR-CT01MAU as sold by Trane in the US |
| Other MA Touch (`M/R_CT01MA*`) controllers | Expected to work (same BLE protocol) — please [open an issue][issues] if you try one |

The BLE protocol is reverse-engineered by the community; it is not an official
Mitsubishi API.

## Before you start

### 1. Enable Bluetooth on each thermostat and get its PIN

1. On the thermostat, open the administrative settings (default code **`0000`**)
   and enable Bluetooth.
2. Open **Settings → Bluetooth**. It shows the **PIN** and the controller's
   **Bluetooth MAC address**. Note both; the MAC tells you which Home Assistant
   device is which.

The PIN is also shown under the key icon on the thermostat's home screen.

### 2. Give Home Assistant a Bluetooth connection to the thermostats

The controllers need a connectable Bluetooth path from Home Assistant:

- **ESP32 Bluetooth proxies** (recommended, and the tested setup). See
  [Bluetooth proxies](#bluetooth-proxies).
- **A Bluetooth adapter on the Home Assistant host**, for one or two thermostats
  within its range.

## Bluetooth proxies

The integration holds one BLE connection per thermostat and spreads them across your
proxies. Proxies are set up in Home Assistant itself; the integration finds and uses
them with no further configuration. The **Prefer Bluetooth proxies** option controls
whether the host's own adapter is used (see [Options](#options)).

### How many you need

An ESPHome proxy in active mode holds about 3 connections at once. Plan one proxy
per 2–3 thermostats, plus one spare so that losing a proxy doesn't take a thermostat
offline:

| Thermostats | Proxies |
|---|---|
| 1–3 | 1 (2 for redundancy) |
| 4–6 | 2 minimum, 3 recommended |
| 7–9 | 3 minimum, 4 recommended |

### Hardware

Any Wi-Fi ESP32 board works. The ESP32-WROOM-32 DevKit (ESP32 DevKitC) costs about
$5–8. Each board needs 5 V USB power near the controllers and 2.4 GHz Wi-Fi.
Pre-flashed Bluetooth proxy devices and PoE ESP32 boards also work.

### Flashing

Open the [ESPHome Bluetooth Proxy installer](https://esphome.github.io/bluetooth-proxies/)
in Chrome or Edge, connect the ESP32 over USB, click **Connect → Install**, and enter
your Wi-Fi details. The firmware needs no further settings.

To manage a proxy from your own ESPHome dashboard instead, start from
[`esphome/bluetooth-proxy.yaml`](esphome/bluetooth-proxy.yaml). It must set
`bluetooth_proxy: active: true`; a passive proxy only relays advertisements and
cannot connect to the thermostats.

### Updating

- **Web-installer boards:** re-run the web installer, or adopt the board into
  ESPHome for OTA updates.
- **ESPHome-managed boards:** update from the ESPHome dashboard. Keep proxies on a
  firmware version that matches your Home Assistant version.

### Adding proxies to Home Assistant

Home Assistant's ESPHome integration discovers a flashed proxy on your network. Open
the discovered ESPHome card under **Settings → Devices & Services** and click
**Configure**. Each proxy then becomes a Bluetooth scanner in Home Assistant, and
this integration starts using it.

### Placement

Place each proxy close enough to its thermostats for a strong signal; walls and
floors weaken 2.4 GHz. The **Active proxy** and **Signal strength** diagnostic
sensors show which proxy serves each thermostat and how strong the link is. "Out of
connection slots" in the Home Assistant log means you need another proxy. Frequent
disconnects on one thermostat mean a proxy should be closer to it.

## Installation

### HACS (recommended)

[![Add App Repository][my-hacs-badge]][my-hacs]

Or add the repository manually:

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/cyaneous/hass-mitsubishi_matouch`, category **Integration**.
2. Install **Mitsubishi MA Touch** and restart Home Assistant.

### Manual

Copy `custom_components/mitsubishi_matouch` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

Home Assistant may show a discovered **Mitsubishi MA Touch** card once a thermostat
is in range. Otherwise go to **Settings → Devices & Services → Add Integration →
Mitsubishi MA Touch**.

1. **Pick** the thermostats to add.
2. **Name and PIN.** Enter a name and the PIN for each thermostat.

### Adding or removing a thermostat later

Each thermostat is a subentry of the integration's single entry:

- **Add:** use the integration's **Add thermostat** action. The other thermostats
  stay connected.
- **Remove:** delete the thermostat's subentry. Its device, entities and connection
  are removed; the others keep running.
- **Rename or change the PIN:** use the subentry's **Reconfigure** action.

### Options

**Settings → Devices & Services → Mitsubishi MA Touch → Configure**:

| Option | Default | Notes |
|---|---|---|
| **Polling interval** (s) | `10` | Minimum `5`. |
| **Prefer Bluetooth proxies over the host's built-in adapter** | on | Connects through a remote Bluetooth proxy (ESPHome, Shelly, …) whenever one can reach the thermostat, even if the host's own adapter has a stronger signal. The host adapter is used only when no proxy is in range. Takes effect on each thermostat's next reconnect. |
| **Log every poll to the telemetry file** | off | Writes each poll to the JSONL log. |
| **Capture raw status frames** | off | Records the raw status frame when it changes, for protocol debugging. |

## Entities

Each thermostat is one Home Assistant device.

### Climate

A `climate` entity with HVAC mode, current temperature, target setpoint (or the
heat/cool range in auto mode), fan speed and swing. Temperatures use your Home
Assistant unit system (see [Fahrenheit](#fahrenheit)).

### Diagnostic sensors

| Sensor | Unit | Meaning |
|---|---|---|
| Connection uptime | s | How long the current BLE connection has been held |
| Reconnects | count | Successful reconnects since startup |
| Disconnects | count | Connection drops |
| Poll latency | ms | Round-trip time of the last status read |
| Active proxy | — | The Bluetooth proxy serving this thermostat |
| Signal strength | dBm | RSSI, measured at connect |

<p align="center">
  <img src="images/diagnostics.png" alt="Per-thermostat diagnostic telemetry on the Home Assistant device page: connection uptime, active proxy, signal strength, poll latency, reconnects, disconnects" width="420">
</p>

## Fahrenheit

The controllers work in Celsius, in 0.5 °C steps. The °F the controller shows comes
from a Mitsubishi lookup table, not the conversion formula: 22.5 °C shows as 72 °F,
where the formula gives 72.5 °F.

- If your Home Assistant unit system is °F, the climate entity reports °F using the
  same table as the MELRemo app, so the card matches the controller and steps in
  whole degrees.
- If it is °C, the values are passed through unchanged.

In °F, setpoints run from 61 °F to 88 °F. 30.5 °C and 31.0 °C both show as 88 °F,
and setting 88 °F selects 31.0 °C, as on the controller.

## Telemetry and diagnostics

- **`mitsubishi_matouch.get_telemetry` service** — returns recent connect,
  disconnect and poll events (latency, proxy, RSSI, uptime). Optional `mac` filter;
  `limit` up to 1000.
- **Download Diagnostics** on the integration — a snapshot with the PIN removed,
  including recent telemetry and proxy assignments.
- **Diagnostic sensors** — for charting in Home Assistant history.
- **JSONL log** in your config directory — off by default; turn on *Log every poll*
  or *Capture raw status frames* in [Options](#options).

## Recovery

- **Idle disconnects:** the controller drops an idle BLE connection after about
  16 s. A keepalive read holds it open.
- **A proxy goes offline:** its thermostats become unavailable while no proxy can
  reach them, and reconnect as soon as a proxy returns.
- **A thermostat is out of range or powered off:** retries back off exponentially,
  with jitter, and return to the normal interval after the first success.
- **Proxies come back or change:** connections are rebalanced evenly across the
  reachable proxies. Rebalancing is debounced, so a flapping proxy does not cause
  repeated moves.
- **Home Assistant restarts or the integration reloads:** connections are
  re-established and rebalanced.
- **Availability:** a thermostat becomes unavailable within about 15–30 s of an
  outage. A single failed poll is tolerated.
- **Changes are confirmed:** a setpoint, mode, fan or swing change is verified after
  it is sent. If it cannot be delivered, the card returns to the real value and Home
  Assistant shows an error.

## Troubleshooting

- **"No MA Touch thermostats found":** no proxy or adapter can reach the thermostat.
  Check that it is powered, that a proxy is online and in range, and that the proxy
  is in active mode. Then click **Search again**.
- **Wrong PIN:** the integration raises a Repairs issue, *"&lt;name&gt;: incorrect
  PIN"*. Enter the PIN from the controller's **Settings → Bluetooth** with the
  thermostat's **Reconfigure** action. The issue clears when the PIN is accepted.
- **`E2` flashes on the controller:** this is shown only on the controller and is
  not in the BLE status frame. The system works normally.
- **`Active proxy` or `Signal strength` show unknown:** expected while a thermostat
  is disconnected; they update on the next connect.

## Credits

This is a fork of
[**cyaneous/hass-mitsubishi_matouch**](https://github.com/cyaneous/hass-mitsubishi_matouch)
by Cyaneous, Inc., which reverse-engineered the MA Touch BLE protocol and wrote the
`btmatouch` protocol library. The fork adds persistent connections, proxy load
balancing, telemetry, config subentries, recovery handling and the Fahrenheit table.

## License

[MIT](LICENSE) © Cyaneous, Inc. (original work). Fork changes are contributed under
the same MIT license.

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[release-badge]: https://img.shields.io/github/v/release/cyaneous/hass-mitsubishi_matouch
[releases]: https://github.com/cyaneous/hass-mitsubishi_matouch/releases
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=cyaneous&repository=hass-mitsubishi_matouch&category=integration
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[issues]: https://github.com/cyaneous/hass-mitsubishi_matouch/issues

# AgentDeck V2: wireless deck with status LCD

V2 outgrows the Creator Micro 2: 20 keys instead of 13, encoder, joystick,
agent-state RGB, on the ESP32-S3 platform (native USB, BLE capable). The
LCD and battery that were in earlier drafts were cut on 2026-08-11: V2 is
USB powered, which keeps the board at V1's power simplicity and the BOM
lean. Battery and screen remain V3/V4 territory.

Target spec against the competition:

| | Creator Micro 2 PRO | AgentDeck V2 |
|---|---|---|
| Keys | 13 mechanical + touch | 20 Kailh Choc hot-swap (4 x 5 grid) |
| Encoder / joystick | 1 / 1 | 1 / 1 (same EC11 + SKQUCAA010) |
| Agent status | per-key RGB | per-key RGB |
| Connectivity | BLE + USB-C | USB-C (BLE capable, USB powered) |
| Battery | 2100 mAh | none (USB powered) |
| Frame | CNC aluminum | printed case (V1 tooling), CNC later |
| Software | proprietary Input app | open firmware + text-file config |

## Clean sheet

V2 is drawn from scratch in `v2/hardware/`: new schematic, new layout, no
copper or project files copied from V1. What carries over is knowledge, not
files - part choices that were already verified, the key spacing, and the
case generator (which is parametric and takes the new outline as input).

## What the market is saying (researched 2026-08-11)

The Codex Micro's reception and the Creator Micro 2's support board are a
map of what to avoid:

- Price is the loudest complaint: $230 reads as "a $100 tax for icon
  keycaps and a software preset" (adityabawankule.io). AgentDeck's DIY
  cost target is the whole answer; keep the V2 BOM lean.
- The real-user complaints on Work Louder's feedback board are software,
  not hardware: the Codex HID session gets stuck in a
  fail-disconnect-reconnect loop, the agent layer dies after the computer
  sleeps until ChatGPT is restarted, and devices "keep getting stuck"
  and need resets.
- Vendor lock-in draws fire: the device only talks to Codex.
- The pragmatic take (echoed across reviews): "the shortcuts are the part
  that actually saves time; the lights are a nice demo." Dedicated
  accept / reject / stop / new-session keys must be first-class.
- The Stream Deck is the benchmark people reach for on status display
  (per-key LCDs) but it lacks the dial and needs Elgato software running.
- The DIY wave (claude-lamp, Claude-Macropad-V2, traffic lights, smart
  bulbs) validates one feature above all: a host-driven "Claude is
  waiting on you" light. And every DIY build is single-session - the
  six-key multi-session panel remains the unmet need.

### Improvements adopted into V2

1. **Survives sleep.** The host bridge re-syncs full LED and LCD state on
   every wake / reconnect event; the device never holds stale state. This
   is the Creator Micro 2's most-reported failure.
2. **No reconnect loops.** Status transport is fire-and-forget HID reports
   with a heartbeat, not a stateful session that can wedge. If the host
   goes quiet the deck shows "host offline" on the LCD and keeps working
   as a plain keyboard.
3. **Standalone first.** Every key sends its chord with no host software
   installed. The bridge only adds status; it is never required.
4. **Agent-agnostic protocol.** The state model (idle / thinking / working
   / blocked / done) is generic; Claude Code is the first backend, not
   the only one. Open protocol, text-file config.
5. **A dedicated STOP key** in the new macro row (Esc / interrupt), the
   single most-requested action key in DIY builds.
6. **Unbrickable recovery.** BOOT and RESET buttons on the ESP32-S3 serial
   bootloader; recovery is a USB cable, never an RMA.
7. **No BLE mode traps.** Explicit radio preference stored on-device, USB
   always wins when plugged in; no triple-tap mode cycling.
8. **The dial stays.** It is the one control the Stream Deck comparison
   concedes; reasoning-effort on a detented knob is a differentiator.

## Architecture

The RP2040 has no radio, so V2 moves to the **ESP32-S3-WROOM-1-N8R2** module
(certified antenna, native USB + BLE HID). This is the same MCU platform the
V3/V4 designs use, so firmware effort is shared: V2 is essentially the V1
control surface on the V3 power/radio platform, in the V1 form factor.

### Display

Wisevision N114-2413THBIG01-H13 (LCSC C2890618, $2.54, in stock):
1.14" IPS, 240x135, ST7789V driver, SPI, 2.4-3.3 V, non-touch.

- Placement: top edge between encoder and joystick, landscape.
- Role: named agent status lines (what the six RGB keys say in colour, the
  LCD says in words), battery %, BLE/USB link state, active layer.
- Interface budget: SPI at 40 MHz plus DC/CS/RST/backlight = 6 GPIO.
- The panel's FPC tail solders directly to the board (the LCSC footprint
  is a direct-solder pad row, 13 pins) - no mating connector needed.
  Backlight is PWM-dimmed through an AO3400A low-side FET.

### Power

- Cell: 103450 LiPo, 2000 mAh, JST-PH 2-pin, protected cell preferred.
- Charging: TP4056 linear charger chain carried from the V3 design
  (stock-checked there), 1 A max, charge LED to the case light pipe.
- Power path: ideal-diode mux so USB powers the board and charges the cell
  simultaneously; battery isolated when USB is present.
- Logic rail: 3.3 V buck (not an AMS1117 - a linear drop from 4.2 V wastes
  20 percent of the cell), low quiescent current for standby.
- LED rail: the SK6812 chain runs from VSYS behind the power switch (the
  V3-proven arrangement) through an AHCT125 level shifter. On USB that is
  5 V; on battery it sags toward 3.7 V, slightly under the SK6812 minimum,
  which works in practice at reduced brightness - the firmware dims on
  battery. A dedicated 5 V boost was considered and dropped: one more
  switcher hurts standby draw more than dim-on-battery hurts the product.
- Budget target: 2 weeks standby, a full work week of active BLE use with
  LEDs at desk brightness. The LCD backlight is the swing item; it gets
  PWM dimming and an idle timeout.

### Keys

20 keys in a 4 x 5 grid at V1 spacing (18.7 x 19.3 mm): the six agent keys
and V1 command set, plus a row of user macro keys. Twenty direct GPIO lines
plus the LCD would not fit, so V2 switches to a 4 x 5 matrix with 1N4148W
diodes (the V3 wiring, parts carried from its manifest). Per-key RGB stays:
the SK6812 chain grows to 20.

The extra row makes the board taller: the outline grows from 95 x 95 to
roughly 95 x 112 mm, with the LCD centred on the new top edge between the
encoder and joystick. The case generator takes the new outline as
parameters.

### GPIO budget (ESP32-S3, ~33 usable)

matrix (4 + 5) + encoder (3) + joystick (5) + LED data (1) + LCD (6) +
battery sense (1) + charge status (1) = 25. Comfortable headroom.

## What carries over from V1 unchanged

- Case generator (`v1/enclosure/src/generate_case.py` re-parameterized
  for the taller outline and battery tray)
- Choc hot-swap sockets, EC11, SKQUCAA010 joystick, SK6812MINI-E LEDs
- USB-C connector and ESD chain
- Keycap icon set

## What is new

- ESP32-S3-WROOM-1-N8R2 module (same part as V3, LCSC C2913204) replaces RP2040 + flash + crystal (all internal
  to the module)
- 20-key 4 x 5 matrix with diodes (V1 was 13 keys direct-wired)
- LCD C2890618 + FPC connector + custom footprint
- Battery, charger, protection, fuel-gauge-by-ADC, 5 V boost, power mux
- Deeper bottom tray (battery sits under the key field, cell is 10.5 mm
  thick, so the tray grows roughly 8 mm)

## Phases

1. Parts manifest (`v2/PARTS.yaml`) with live LCSC stock checks - DONE
2. LCD footprint + symbol - DONE (pulled from LCSC, direct-solder FPC)
3. Schematic - DONE: `v2/tools/gen_schematic.py` generates
   `v2/hardware/AgentDeckV2.kicad_sch`; ERC 0 errors, 0 warnings
   (board grew to 112 x 112 mm during layout - 5 columns at V1 key
   spacing plus the top control strip need the full square)
4. Layout - DONE: `v2/tools/place_pcb.py` + `export_dsn.py` +
   freerouting + `finish_v2.py`. 112 x 112 mm, 4 copper layers,
   126 footprints, fully routed: 0 DRC errors, 0 unconnected.
   GND flooded on all four layers, VSYS_SW LED pour on B.Cu,
   antenna keep-out at the top edge, designators on silk.
5. Case: re-run the V1 generator with a deeper tray and LCD window - TODO
6. Firmware: V3 firmware tree, V1 keymap, LCD status page - TODO
7. Fab outputs (gerbers, BOM, CPL) - TODO

## Open questions

- BASE variant (no battery, no radio, keep the LCD) as a cheaper build?
- Fuel gauge IC vs plain ADC divider (start with ADC, pads for MAX17048)
- Whether the LCD FPC connector is hand-solderable (0.5 mm pitch usually
  is, with flux and patience) - matters because V2 targets JLCPCB PCBA
  anyway, so only a nice-to-have

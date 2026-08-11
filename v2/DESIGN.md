# AgentDeck V2: wireless deck with status LCD

V2 competes head-on with the Work Louder Creator Micro 2 PRO. Same brief:
13 keys, encoder, joystick, agent-state RGB, but wireless with a built-in
battery, plus a small always-on status screen the Creator Micro does not have.

Target spec against the competition:

| | Creator Micro 2 PRO | AgentDeck V2 |
|---|---|---|
| Keys | 13 mechanical + touch | 13 Kailh Choc hot-swap (V1 layout carried) |
| Encoder / joystick | 1 / 1 | 1 / 1 (same EC11 + SKQUCAA010) |
| Agent status | per-key RGB | per-key RGB + 1.14" LCD text panel |
| Connectivity | BLE + USB-C | BLE + USB-C |
| Battery | 2100 mAh | 2000 mAh LiPo (103450 cell) |
| Frame | CNC aluminum | printed case (V1 tooling), CNC later |
| Software | proprietary Input app | open firmware + text-file config |

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
- The panel is an FPC part; footprint and mating connector need drawing
  from the Wisevision datasheet before layout (same custom-footprint flow
  as the V1 joystick).

### Power

- Cell: 103450 LiPo, 2000 mAh, JST-PH 2-pin, protected cell preferred.
- Charging: TP4056 linear charger chain carried from the V3 design
  (stock-checked there), 1 A max, charge LED to the case light pipe.
- Power path: ideal-diode mux so USB powers the board and charges the cell
  simultaneously; battery isolated when USB is present.
- Logic rail: 3.3 V buck (not an AMS1117 - a linear drop from 4.2 V wastes
  20 percent of the cell), low quiescent current for standby.
- LED rail: SK6812MINI-E wants 3.7-5.5 V, which a sagging cell cannot
  guarantee, so the LEDs run from a small 5 V boost behind a load switch.
  On battery the firmware dims or duty-cycles the chain; standby cuts the
  rail entirely.
- Budget target: 2 weeks standby, a full work week of active BLE use with
  LEDs at desk brightness. The LCD backlight is the swing item; it gets
  PWM dimming and an idle timeout.

### GPIO budget (ESP32-S3, ~33 usable)

13 keys + encoder (3) + joystick (5) + LED data (1) + LCD (6) +
battery sense (1) + charge status (1) = 30. No matrix, same as V1.

## What carries over from V1 unchanged

- Board outline, mounting holes, case generator (`v1/enclosure/src/
  generate_case.py` re-parameterized for the taller battery tray)
- Choc hot-swap sockets, EC11, SKQUCAA010 joystick, SK6812MINI-E LEDs
- USB-C connector and ESD chain
- Keycap icon set

## What is new

- ESP32-S3-WROOM-1-N8R2 module (same part as V3, LCSC C2913204) replaces RP2040 + flash + crystal (all internal
  to the module)
- LCD C2890618 + FPC connector + custom footprint
- Battery, charger, protection, fuel-gauge-by-ADC, 5 V boost, power mux
- Deeper bottom tray (battery sits under the key field, cell is 10.5 mm
  thick, so the tray grows roughly 8 mm)

## Phases

1. Parts manifest (`v2/PARTS.yaml`) with live LCSC stock checks - the
   V3 pattern, enforced by the same verify script
2. LCD footprint + symbol from the Wisevision datasheet
3. Schematic: V1 input blocks + V3 power blocks + LCD
4. Layout in the V1 95 x 95 outline; battery keep-out and antenna keep-out
   are the two new placement constraints (module antenna must overhang a
   copper-free zone at the board edge)
5. Case: re-run the V1 generator with a deeper tray and LCD window
6. Firmware: V3 firmware tree, V1 keymap, LCD status page

## Open questions

- BASE variant (no battery, no radio, keep the LCD) as a cheaper build?
- Fuel gauge IC vs plain ADC divider (start with ADC, pads for MAX17048)
- Whether the LCD FPC connector is hand-solderable (0.5 mm pitch usually
  is, with flux and patience) - matters because V2 targets JLCPCB PCBA
  anyway, so only a nice-to-have

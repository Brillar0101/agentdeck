# Changelog

All notable changes to AgentDeck are recorded here. The board is text-based
KiCad, so each fabricated revision maps to a tagged commit: a physical board can
be traced back to the exact design it was made from.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions are hardware revisions, not software releases.

## [Unreleased]

### V2 (redesigned)
- V2 redefined as a wireless Creator Micro 2 PRO competitor: V1 control
  surface on the V3 ESP32-S3 power/radio platform. BLE + USB-C, built-in
  2000 mAh 103450 LiPo, 20 keys in a diode matrix, and a 1.14" 240x135 ST7789V status LCD (LCSC
  C2890618, stock-confirmed). Replaces the earlier PowerDeck two-deck
  concept. Design doc `v2/DESIGN.md`, parts manifest `v2/PARTS.yaml`.

### V4 (started)
- Voice + screen successor under `v4/`: V3 platform plus I2S MEMS mic with
  on-device wake word (ESP-SR), NS4168 class-D amp + speaker, 1.69" 240x280
  ST7789 touch LCD (replaces the supply-fragile 0.96" OLED), second EC11.
- Scaffold: `v4/DESIGN.md` (deltas, audio placement rules 11-14, phase
  plan) and `v4/PARTS.yaml` (carried lines live-confirmed 2026-07-29; new
  audio/LCD lines stock-checked - NS4168 confirmed, mic and LCD gated VERIFY).

### V3 (in progress)
- New hand-solderable version under `v3/`: ESP32-S3-WROOM, 24-key 4x6 Choc matrix,
  0.96" OLED, capacitive touch PTT, LiPo + TP4056 charging, USB-C + BLE HID.
- Parts manifest `v3/PARTS.yaml` (2D/3D dims, LCSC stock) enforced by
  `v3/tools/verify_parts.py`; design doc `v3/DESIGN.md`; V3 tools are
  git-tracked (unlike V1 generators).

## [1.0.0] - 2026-08-11

The V1 release. Everything below was re-verified end to end: 0 DRC errors,
0 unconnected nets, 0 ERC errors. Still nothing manufactured.

### Hardware
- Board grown from 90 x 90 to 95 x 95 mm. Mounting holes moved 2 mm out
  along the corner diagonals so the screw bosses clear the switch field.
- Full reroute on the larger outline (autorouter for the bulk, interactive
  push-and-shove for the congested RP2040 escape). Copper pours expanded to
  the new edge.
- USB-C moved to the top edge and nudged up; RP2040 moved 2 mm down.
- ERC clean: the USBLC6 ESD taps were re-declared as passive pins.
- BOM corrected (27R USB series resistors, was a 27k part number) and
  extended with the case fasteners: M2.5 x 8 button-head screws, brass
  heat-set inserts, printed cover caps.

### Enclosure
- Case is now parametric: `v1/enclosure/src/generate_case.py` builds both
  shells and the cover caps from measured board geometry. Watertight STLs,
  screw axes coaxial with the PCB holes to 0.003 mm.
- Measured fastener stack: lid counterbore 5.2 x 2.5 mm over a 2.9 mm shaft,
  through the 2.7 mm PCB hole, into a 4.0 mm OD x 5.0 mm heat-set insert.
- USB access is a side port through the tray wall (the connector hangs below
  the board), sized for the plug plus a slim cable overmould.
- 0.6 mm edge bevels so printed parts read as moulded.
- Keycaps carry Lucide icon decals (dice for the agent keys, thumbs up/down
  for accept/reject); all text legends removed. Encoder and joystick caps
  are white.

### Docs
- Photoreal render pipeline and reference renders under `docs/img/`.
- README restructured for the release.

## [0.1.0] - 2026-07-24

First complete, DRC-clean revision. Nothing has been manufactured or
hardware-verified yet.

### Hardware
- 90 x 90 mm 4-layer PCB, fully routed, 0 DRC errors.
- 13 Kailh Choc hot-swap keys with per-key SK6812MINI-E reverse-mount RGB.
- EC11 rotary encoder and Alps SKQUCAA010 5-way joystick.
- RP2040 with W25Q128 flash, USB-C, BOOT button, SWD pads.
- All 13 LEDs positioned under their key caps (4.8 mm north of each switch
  pole hole), so light shines up through the cap rather than into the row gap.

### Firmware
- CircuitPython firmware for all 13 keys, encoder, joystick, and the LED chain.
- Six agent keys show live agent state by colour; command keys send Ctrl+Alt
  chords; FN layer key.

### Host
- `host/agentdeck_bridge.py` maps Claude Code hooks to agent-key colours.

### Enclosure
- Two-part printable case (bottom + plate lid) plus cover plugs, modelled in
  Blender and exported to STL. Not yet printed.

### Fab
- Gerbers, drill, BOM, and CPL generated for JLCPCB.

[Unreleased]: https://github.com/Brillar0101/agentdeck/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Brillar0101/agentdeck/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/Brillar0101/agentdeck/releases/tag/v0.1.0

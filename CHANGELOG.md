# Changelog

All notable changes to ClaudeMicro are recorded here. The board is text-based
KiCad, so each fabricated revision maps to a tagged commit: a physical board can
be traced back to the exact design it was made from.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions are hardware revisions, not software releases.

## [Unreleased]

### V4 (started)
- Voice + screen successor under `v4/`: V3 platform plus I2S MEMS mic with
  on-device wake word (ESP-SR), NS4168 class-D amp + speaker, 1.69" 240x280
  ST7789 touch LCD (replaces the supply-fragile 0.96" OLED), second EC11.
- Scaffold: `docs/DESIGN-V4.md` (deltas, audio placement rules 11-14, phase
  plan) and `v4/PARTS.yaml` (carried lines live-confirmed 2026-07-29; new
  audio/LCD lines stock-checked - NS4168 confirmed, mic and LCD gated VERIFY).

### V3 (in progress)
- New hand-solderable version under `v3/`: ESP32-S3-WROOM, 24-key 4x6 Choc matrix,
  0.96" OLED, capacitive touch PTT, LiPo + TP4056 charging, USB-C + BLE HID.
- Parts manifest `v3/PARTS.yaml` (2D/3D dims, LCSC stock) enforced by
  `v3/tools/verify_parts.py`; design doc `docs/DESIGN-V3.md`; V3 tools are
  git-tracked (unlike V1 generators).

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
- `host/claude_bridge.py` maps Claude Code hooks to agent-key colours.

### Enclosure
- Two-part printable case (bottom + plate lid) plus cover plugs, modelled in
  Blender and exported to STL. Not yet printed.

### Fab
- Gerbers, drill, BOM, and CPL generated for JLCPCB.

[Unreleased]: https://github.com/Brillar0101/claude-micro/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Brillar0101/claude-micro/releases/tag/v0.1.0

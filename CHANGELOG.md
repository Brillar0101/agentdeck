# Changelog

All notable changes to ClaudeMicro are recorded here. The board is text-based
KiCad, so each fabricated revision maps to a tagged commit: a physical board can
be traced back to the exact design it was made from.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions are hardware revisions, not software releases.

## [Unreleased]

Nothing yet.

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

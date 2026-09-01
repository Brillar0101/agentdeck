# Changelog

All notable changes to AgentDeck are recorded here. The board is text-based
KiCad, so each fabricated revision maps to a tagged commit: a physical board can
be traced back to the exact design it was made from.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions are hardware revisions, not software releases.

## [Unreleased]

### V2 (wireless platform, in design)
- New `v2/`: the V3 ESP32-S3 / LiPo / BLE platform recovered from history
  (pre-297fabb) and re-cut to the roadmap's 20-key 4x5 control surface.
  Row 0 is the fixed system row (INT / PTT / REC / MODE / DND).
- Touch pad removed; Alps SKQUCAA010 5-way joystick (V1 part) added on
  GPIO15/16/17/18 + GPIO1. Battery pocket regrown to 34x50 mm for a 103450
  2000 mAh cell on the right-hand strip; board stays 150x110 mm.
- Schematic, symbol lib, netlist, placement and routing are script-generated
  (`v2/tools`), ERC clean (0 errors; 72 pin-type warnings from vendor
  symbols with "unspecified" pin types).
- Stays 2-layer. The USB pair and the module decoupling comb are pre-routed
  and locked; the USB-C clearance marker is no longer exported as a router
  keepout. Links the scripted flow leaves open are hand-routed in KiCad.
- Firmware re-cut for 20 keys, 3 modes, joystick `J` lines, system-row
  roles via `K` lines, agent slots 1-8.
- Charger stays TP4056 + load-share and battery level stays ADC: BQ24074 /
  fuel-gauge parts break the hand-solder floor (recorded in ROADMAP).
- Sourcing pass against the JLCPCB assembly library (2026-09-01): every
  symbol now carries an `LCSC` field; `v2/fab/` holds the JLCPCB BOM, CPL
  and consigned-parts list. LDO swapped ME6211C33 -> RT9080-33GJ5 (stock),
  joystick swapped SKQUCAA010 (THT, unstocked) -> SKRHABE010 (SMD, C139794)
  with the JLC library footprint. STEP models for all library parts pulled
  into `v2/hardware/jlc3d` (`tools/attach_3d.py` wires them into a board).
- Removed the unbuilt V2-V4 paper designs (297fabb). The project refocuses on
  manufacturing and validating V1 before any successor is designed.

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

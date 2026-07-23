# ClaudeMicro

A 90 × 90 mm RP2040 desk macropad: 13 Kailh Choc hot-swap keys with per-key RGB,
a rotary encoder, a 5-way joystick, and USB-C — on a 4-layer PCB, with a printable
two-part enclosure.

The idea behind it: a tactile control surface for supervising AI coding agents.
Six "agent" keys light up to show each agent's state (idle / thinking / working /
blocked / done), command keys accept or reject work, and the dial and joystick
handle scrubbing and navigation.

> **This is a Codex Micro-inspired project.** The concept follows OpenAI and
> Work Louder's **Codex Micro**, and the control layout deliberately echoes it.
> It is an independent build — **not affiliated with, endorsed by, or produced
> with OpenAI, Work Louder, or Anthropic.** The board, firmware and enclosure
> here are original work; no Codex Micro files were used. Some material in this
> repository (vendor footprints, datasheets, reference photographs, third-party
> cap and knob models) is **not ours to license** — see
> [LICENSING.md](LICENSING.md).

## Status

| Part | State |
|---|---|
| Schematic + PCB | Complete — 4 layers, fully routed, **0 DRC errors** |
| Firmware | Written (CircuitPython), untested on hardware |
| Host bridge | Written — maps Claude Code hooks to agent-key colours |
| Enclosure | Modelled, STLs exported, not yet printed |
| Fab package | Gerbers / BOM / CPL generated (regenerate after board edits) |

Nothing has been manufactured yet, so none of it is hardware-verified.

## Layout

- **13 keys** on an 18.7 × 19.3 mm grid — 6 agent keys (colour = live agent
  state), accept / reject / new-chat / model keys, a wide push-to-talk key,
  a macro key, and an FN layer key
- **EC11 rotary encoder** (top-left) and **Alps SKQUCAA010 5-way joystick** (top-right)
- **SK6812MINI-E** reverse-mount RGB under each key
- **USB-C** on the rear face; W25Q128 flash; BOOT button; SWD pads

## Repository

```
ClaudeMicro.kicad_pcb / .kicad_sch     board and schematic
JLC.pretty/ JLC.3dshapes/ *.kicad_sym  footprint, 3D and symbol libraries
fab/                                   Gerbers, BOM and CPL for JLCPCB
firmware/                              CircuitPython firmware (boot.py, code.py)
host/claude_bridge.py                  host-side agent-status bridge
enclosure/                             Blender assembly, case STLs, cap/knob models
tools/                                 board and case generation scripts
docs/                                  design notes, datasheets, reference material
LICENSES/                              full licence texts
```

## Enclosure

Two printed parts plus four cover plugs, clamping the PCB between a bottom case
and a plate-style lid:

| Feature | Spec |
|---|---|
| Heat-set inserts | M2.5 × 0.45, OD 4.0 mm, length 4.0 mm — boss pilot Ø3.6 × 5.5 mm |
| Screws | M2.5 × 8 mm countersunk (ISO 7046), head Ø5.0 × 1.05 mm |
| Stack | 2.4 mm floor · 4.0 mm cavity · PCB 1.6 mm · 3.9 mm lid |
| Key openings | 17.4 mm (switch body 15.0 + 1.2 mm per side) |
| Travel clearance | 1.84 mm before a cap meets the plate |

Print `enclosure/case-bottom.stl`, `enclosure/case-top-lid.stl`, and 4x `enclosure/case-cover-plug.stl`.

## Firmware

Copy `firmware/boot.py` and `code.py` onto a CIRCUITPY drive running
CircuitPython 9.x, with `adafruit_hid` and `neopixel` in `lib/`.

Six agent keys show each agent's live state (idle / thinking / working /
blocked / done); accept, reject, new-chat, model, push-to-talk and macro keys
send Ctrl+Alt chords; the dial sets reasoning effort and the joystick navigates.
`firmware/README.md` has the full control table, colour legend, pin map, and the
three constants to confirm on first hardware.

## Regenerating

The autorouter jar is not committed — download
[freerouting](https://github.com/freerouting/freerouting/releases) to `tools/`.
Board 3D exports and the routing `.dsn`/`.ses` files are derived and also excluded.

## Licence

Multi-licensed, as is normal for open hardware — see [LICENSING.md](LICENSING.md).

| What | Licence |
|---|---|
| Software (`firmware/`, `host/`, `tools/`) | [MIT](LICENSES/MIT.txt) |
| Hardware (board, enclosure, fab files) | [CERN-OHL-S v2](LICENSES/CERN-OHL-S-v2.txt) |
| Documentation | [CC-BY-4.0](LICENSES/CC-BY-4.0.txt) |

Vendor footprints, datasheets and reference images keep their original terms.

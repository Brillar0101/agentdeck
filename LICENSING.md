# Licensing

AgentDeck is an open-hardware project, so different parts carry different
licences. This is the usual split for open hardware — one licence cannot sensibly
cover source code, a PCB design, and written documentation at once.

| What | Covers | Licence |
|---|---|---|
| **Software** | `firmware/`, `host/`, `*.py` | [MIT](LICENSES/MIT.txt) |
| **Hardware** | `*.kicad_pcb`, `*.kicad_sch`, `*.kicad_sym`, `*.pretty/`, `fab/`, `enclosure/*.stl`, `enclosure/*.blend`, enclosure models | [CERN-OHL-S v2](LICENSES/CERN-OHL-S-v2.txt) |
| **Documentation** | `README.md`, `DESIGN.md`, `PLAN.md`, `*/README.md`, images | [CC-BY-4.0](LICENSES/CC-BY-4.0.txt) |

SPDX identifiers: `MIT`, `CERN-OHL-S-2.0`, `CC-BY-4.0`.

The root `LICENSE` file is the MIT text so GitHub reports a licence; it applies
to the software only. Hardware and documentation are governed by the table above.

## What each one means

**MIT** (software) — do anything, including commercially and in closed products;
just keep the copyright notice. No warranty.

**CERN-OHL-S v2** (hardware) — *strongly reciprocal*. You may study, modify,
manufacture and sell the board and enclosure, but if you distribute a modified
design, or a product made from it, you must release your design sources under
CERN-OHL-S as well. This keeps derivatives open.

**CC-BY-4.0** (documentation) — reuse and adapt the writing and figures, with
attribution.

### If you would rather not have the share-alike condition

Swap the hardware licence to [CERN-OHL-P v2](https://ohwr.org/project/cernohl)
(permissive — no obligation to publish your modifications). That is a one-file
change plus an edit to the table above. CERN-OHL-S was chosen as the default
because it keeps improvements to the board flowing back to the community.

## Third-party material

Some content in this repository is **not** covered by the licences above and
remains under its original terms:

- `JLC.3dshapes/`, `JLC.pretty/` — component footprints and 3D models from LCSC /
  JLCPCB and their manufacturers
- `docs/datasheets/`, `docs/reference/*.pdf` — vendor documentation (Raspberry Pi,
  Alps and others), redistributed for reference only
- `docs/reference/*.webp`, `docs/reference/*.png` — **product photographs of
  OpenAI / Work Louder's Codex Micro.** These are not ours, are used only as
  design reference, and are **not** licensed for redistribution. Remove them
  before making this repository public.
- `docs/reference/pi-codex-micro/` — a clone of a third-party project
  (github.com/jal-co/pi-codex-micro) under its own licence; excluded from git
- `enclosure/keycaps/`, `enclosure/encoder/` — keycap and knob models sourced from their
  respective authors; check the original terms before redistributing

## Inspiration and independence

AgentDeck is an **independent, Codex Micro-inspired project**. The idea of a
macropad for supervising coding agents — agent keys that show live state, an
accept/reject pair, a reasoning-effort dial — follows OpenAI and Work Louder's
**Codex Micro**, and the layout here deliberately echoes it.

This project is **not affiliated with, endorsed by, or produced in cooperation
with OpenAI, Work Louder, or Anthropic.** The schematic, PCB layout, firmware and
enclosure in this repository are original work; no files from the Codex Micro were
used. "Codex", "Codex Micro", "OpenAI", "Work Louder", "Claude" and "Anthropic"
are trademarks of their respective owners, referenced here only descriptively.
The "AgentDeck" name is a working project name, not a product name, and carries
no claim to Anthropic's marks.

## Attribution

Copyright (c) 2026 Brillar0101 — for the original work only. Third-party material
listed above stays with its owners.

There is no warranty. Nothing in this repository has been manufactured or
hardware-verified — see the status table in the README.

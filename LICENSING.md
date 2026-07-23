# Licensing

ClaudeMicro is an open-hardware project, so different parts carry different
licences. This is the usual split for open hardware — one licence cannot sensibly
cover source code, a PCB design, and written documentation at once.

| What | Covers | Licence |
|---|---|---|
| **Software** | `firmware/`, `host/`, `tools/`, `*.py` | [MIT](LICENSES/MIT.txt) |
| **Hardware** | `*.kicad_pcb`, `*.kicad_sch`, `*.kicad_sym`, `*.pretty/`, `fab/`, `3d/*.stl`, `3d/*.blend`, enclosure models | [CERN-OHL-S v2](LICENSES/CERN-OHL-S-v2.txt) |
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
- `datasheets/`, `reference/*.pdf` — vendor documentation (Raspberry Pi, Alps,
  and others), redistributed for reference only
- `reference/*.webp`, `reference/*.png` — third-party product images, used for
  design reference and not licensed for redistribution
- `3d/keycaps/`, `3d/encoder/` — keycap and knob models sourced from their
  respective authors; check the original terms before redistributing
- `tools/freerouting.jar` is **not** included; download it separately
  ([freerouting](https://github.com/freerouting/freerouting), GPL-3.0)

## Attribution

Copyright (c) 2026 Brillar0101.

There is no warranty. Nothing in this repository has been manufactured or
hardware-verified — see the status table in the README.

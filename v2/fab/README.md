# V2 fabrication package (JLCPCB)

Sourcing was re-checked against the JLCPCB assembly library on 2026-09-01
(every LCSC code in `../PARTS.yaml`, stock and basic/extended status).

| File | What |
|---|---|
| `jlcpcb-bom.csv` | JLCPCB BOM (Comment, Designator, Footprint, LCSC Part #) - 27 lines, 119 placements |
| `jlcpcb-cpl.csv` | JLCPCB pick-and-place, filtered to BOM designators |
| `consigned-parts.csv` | parts JLCPCB does not stock: prog pads (no part), battery |
| `kicad-pos.csv` | raw KiCad position export the CPL was made from |

Regenerate the CPL after routing changes nothing - positions are fixed - but
regenerate both files if the schematic changes:

    kicad-cli pcb export pos --format csv --units mm --side both --exclude-dnp \
        -o v2/fab/kicad-pos.csv v2/hardware/AgentDeckV2.kicad_pcb
    python3 ~/.claude/skills/bom/scripts/translate_bom_pnp.py pnp \
        v2/fab/kicad-pos.csv -o v2/fab/jlcpcb-cpl.csv --bom v2/fab/jlcpcb-bom.csv

The schematic symbols carry an `LCSC` field, so KiCad's own BOM export
(Reference/Value/Footprint/LCSC -> Designator/Comment/Footprint/LCSC Part #)
reproduces `jlcpcb-bom.csv`.

## Library status (2026-09-01)

- Basic (no feeder fee): 1N4148W, AO3401A, SS34, tact switches, every
  resistor and capacitor.
- Extended ($3 each): ESP32-S3-WROOM-1-N8R2, SK6812MINI-E, SN74AHCT1G125,
  EC11 encoder, USB-C, USBLC6-2SC6, TP4056, RT9080-33GJ5, JST-PH, MSK12C02,
  SKRHABE010 joystick - 11 parts, ~$33 of feeder fees per order.
- Swapped for stock: LDO ME6211C33 (17 in stock) -> RT9080-33GJ5 C841192
  (same SOT-23-5 pinout, 600 mA, 2 uA Iq). Joystick SKQUCAA010 (THT, not
  stocked) -> SKRHABE010 C139794 (SMD, 4.7k in stock).
- Kailh Choc CPG135001D01/02/03 (C400229/230/231) ARE in the library but at
  zero stock - consigned until they restock; hand-soldered anyway (THT).
- The 0.96" OLED is the JLCPCB library module C5248080 (HS96L03W2C03, 4-pin
  THT header) with JLC's own footprint and STEP model.

## 3D models

`../hardware/jlc3d/JLC.3dshapes/*.step` were pulled from JLCPCB/EasyEDA per
LCSC code (`easyeda2kicad --3d --lcsc_id=Cxxxxx`). V2.pretty footprints
reference them; for the other footprints run, with KiCad closed:

    <KiCad python> v2/tools/attach_3d.py

then check the 3D viewer - EasyEDA models occasionally need a 90/180 turn.

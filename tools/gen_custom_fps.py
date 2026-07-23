#!/usr/bin/env python3
"""Generate ClaudeMicro.pretty custom footprints.

1. SKQUCAA010 - Alps 5-way navigation switch, SNAP-IN THT variant.
   Geometry from the Alps SKQU series catalog (reference/SKQUCAA010.pdf,
   p.3 drawing 3): two columns 10.3mm apart, 3 holes each; outer 4 holes
   drill 1.2mm, middle pair drill 1.0mm; outer rows at +/-3.25mm, middle
   row offset +0.45mm; stem rotation center 1.23mm toward pin 1/6 row.
   Pins: 1=A 2=B 3=C (left, top->bottom), 6=Center 5=D 4=Common (right).
2. TouchPad_D12 - 12mm circular copper electrode for the TTP223, kept
   UNDER soldermask (datasheet allows a dielectric panel over the pad;
   mask acts as the panel). Single SMD pad, F.Cu only.
3. ProgPads_1x4 - bare SWD pads (SWCLK, SWDIO, GND, RUN), 2.54mm pitch,
   modeled on NeuralCard's ProgPads.
"""
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "ClaudeMicro.pretty")
os.makedirs(OUT, exist_ok=True)


def write(name, body):
    path = os.path.join(OUT, f"{name}.kicad_mod")
    open(path, "w").write(body)
    print("wrote", os.path.normpath(path))


# ---- SKQUCAA010 ----
XCOL = 5.15
pads = [
    ("1", -XCOL, -3.25, 1.2), ("2", -XCOL, 0.45, 1.0), ("3", -XCOL, 3.25, 1.2),
    ("6", XCOL, -3.25, 1.2), ("5", XCOL, 0.45, 1.0), ("4", XCOL, 3.25, 1.2),
]
pad_lines = []
for num, x, y, drill in pads:
    dia = drill + 0.7
    pad_lines.append(
        f'  (pad "{num}" thru_hole circle (at {x} {y}) (size {dia} {dia})'
        f' (drill {drill}) (layers "*.Cu" "*.Mask"))')
body = "\n".join([
    '(footprint "SKQUCAA010"',
    '  (version 20240108) (generator "gen_custom_fps")',
    '  (layer "F.Cu")',
    '  (descr "Alps SKQUCAA010 5-way nav switch, snap-in THT, 10x10mm body,'
    ' 1.6mm PCB per datasheet")',
    '  (attr through_hole)',
    '  (fp_text reference "JS1" (at 0 -6.4) (layer "F.SilkS")'
    ' (effects (font (size 1 1) (thickness 0.15))))',
    '  (fp_text value "SKQUCAA010" (at 0 6.4) (layer "F.Fab")'
    ' (effects (font (size 1 1) (thickness 0.15))))',
    # body outline + stem rotation center mark (offset 1.23mm)
    '  (fp_rect (start -5 -5) (end 5 5) (stroke (width 0.12) (type solid))'
    ' (fill none) (layer "F.SilkS"))',
    '  (fp_circle (center 0 -1.23) (end 2.975 -1.23) (stroke (width 0.1)'
    ' (type solid)) (fill none) (layer "F.Fab"))',
    '  (fp_rect (start -6 -5.5) (end 6 5.5) (stroke (width 0.05) (type solid))'
    ' (fill none) (layer "F.CrtYd"))',
] + pad_lines + [')'])
write("SKQUCAA010", body)

# ---- TouchPad_D12: covered electrode (F.Cu only, no mask opening) ----
body = "\n".join([
    '(footprint "TouchPad_D12"',
    '  (version 20240108) (generator "gen_custom_fps")',
    '  (layer "F.Cu")',
    '  (descr "TTP223 sense electrode 12mm, covered by soldermask (mask=panel)")',
    '  (attr exclude_from_pos_files exclude_from_bom allow_missing_courtyard)',
    '  (fp_text reference "TP1" (at 0 -7.2) (layer "F.Fab") (hide yes)'
    ' (effects (font (size 1 1) (thickness 0.15))))',
    '  (fp_text value "TOUCH" (at 0 7.2) (layer "F.Fab") (hide yes)'
    ' (effects (font (size 1 1) (thickness 0.15))))',
    '  (pad "1" smd circle (at 0 0) (size 12 12) (layers "F.Cu"))',
    ')'])
write("TouchPad_D12", body)

# ---- ProgPads_1x4: SWCLK SWDIO GND RUN ----
labels = ["SWCLK", "SWDIO", "GND", "RUN"]
lines = [
    '(footprint "ProgPads_1x4"',
    '  (version 20240108) (generator "gen_custom_fps")',
    '  (layer "F.Cu")',
    '  (descr "Bare SWD/debug pads, 2.54mm pitch, flash-once like NeuralCard")',
    '  (attr smd exclude_from_pos_files exclude_from_bom)',
    '  (fp_text reference "J2" (at -3.8 0 90) (layer "F.SilkS")'
    ' (effects (font (size 0.9 0.9) (thickness 0.15))))',
    '  (fp_text value "SWD" (at 0 3.4) (layer "F.Fab") (hide yes)'
    ' (effects (font (size 0.9 0.9) (thickness 0.15))))',
]
for i, lab in enumerate(labels):
    x = (i - 1.5) * 2.54
    lines.append(f'  (pad "{i+1}" smd rect (at {x} 0) (size 1.7 2.4)'
                 f' (layers "F.Cu" "F.Mask"))')
    lines.append(f'  (fp_text user "{lab}" (at {x} -1.9) (layer "F.SilkS")'
                 f' (effects (font (size 0.7 0.7) (thickness 0.12))))')
lines.append(')')
write("ProgPads_1x4", "\n".join(lines))

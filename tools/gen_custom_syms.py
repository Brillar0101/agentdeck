#!/usr/bin/env python3
"""Generate ClaudeMicro_Custom.kicad_sym: real schematic symbols for the
parts that have no vendor symbol — the Alps 5-way joystick (drawn as a
directional switch, pins named for the datasheet contacts), the TTP223
touch electrode, and the SWD programming pads.
"""
import os


def pin(num, name, x, y, angle, ptype="passive", length=5.08):
    return (f'      (pin {ptype} line (at {x} {y} {angle}) (length {length})\n'
            f'        (name "{name}" (effects (font (size 1.27 1.27))))\n'
            f'        (number "{num}" (effects (font (size 1.27 1.27))))\n'
            f'      )')


def sym(name, ref, graphics, pins, value=None):
    value = value or name
    return f'''  (symbol "{name}"
    (pin_names (offset 1.016))
    (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "{ref}" (at 0 10.16 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{value}" (at 0 -10.16 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Description" "" (at 0 0 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "{name}_0_1"
{graphics}
    )
    (symbol "{name}_1_1"
{pins}
    )
  )'''


symbols = []

# ---- SKQUCAA010: 4 directions + center push + common ----
g = '''      (rectangle (start -7.62 -7.62) (end 7.62 7.62)
        (stroke (width 0.254) (type default)) (fill (type background)))
      (circle (center 0 0) (radius 2.54)
        (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 0 4.45) (xy 0 3.18))
        (stroke (width 0.381) (type default)) (fill (type none)))
      (polyline (pts (xy 0 -4.45) (xy 0 -3.18))
        (stroke (width 0.381) (type default)) (fill (type none)))
      (polyline (pts (xy -4.45 0) (xy -3.18 0))
        (stroke (width 0.381) (type default)) (fill (type none)))
      (polyline (pts (xy 4.45 0) (xy 3.18 0))
        (stroke (width 0.381) (type default)) (fill (type none)))'''
p = "\n".join([
    pin("1", "A_UP", -12.7, 5.08, 0),
    pin("2", "B_LEFT", -12.7, 0, 0),
    pin("3", "C_DOWN", -12.7, -5.08, 0),
    pin("6", "CENTER", 12.7, 5.08, 180),
    pin("5", "D_RIGHT", 12.7, 0, 180),
    pin("4", "COM", 12.7, -5.08, 180),
])
symbols.append(sym("SKQUCAA010", "JS", g, p))

# ---- TouchPad: electrode ----
g = '''      (circle (center 0 1.27) (radius 3.175)
        (stroke (width 0.254) (type default)) (fill (type none)))
      (circle (center 0 1.27) (radius 1.905)
        (stroke (width 0.254) (type default)) (fill (type none)))
      (circle (center 0 1.27) (radius 0.635)
        (stroke (width 0.254) (type default)) (fill (type outline)))'''
p = pin("1", "PAD", 0, -7.62, 90, length=3.81)
symbols.append(sym("TouchPad", "TP", g, p, value="TOUCH"))

# ---- ProgPads_1x4: SWD/debug pads ----
g = '''      (rectangle (start -7.62 -6.35) (end 2.54 6.35)
        (stroke (width 0.254) (type default)) (fill (type background)))'''
p = "\n".join([
    pin("1", "SWCLK", -12.7, 3.81, 0),
    pin("2", "SWDIO", -12.7, 1.27, 0),
    pin("3", "GND", -12.7, -1.27, 0),
    pin("4", "RUN", -12.7, -3.81, 0),
])
symbols.append(sym("ProgPads_1x4", "J", g, p, value="SWD"))

out = ('(kicad_symbol_lib\n  (version 20241209)\n  (generator "gen_custom_syms")\n'
       '  (generator_version "9.0")\n' + "\n".join(symbols) + "\n)\n")
path = os.path.join(os.path.dirname(__file__), "..", "ClaudeMicro_Custom.kicad_sym")
open(path, "w").write(out)
print("wrote", os.path.normpath(path), f"({len(symbols)} symbols)")

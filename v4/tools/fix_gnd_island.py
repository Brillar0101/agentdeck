#!/usr/bin/env python3
"""Join the stranded C3-pad-2 GND island to main GND with a B.Cu jumper.

The island (F.Cu, x 18.7..22.9, y 19.7..22.1) is fenced on F.Cu by the U1 pad
row to the north, the +3V3 run to the south, and the I2S_DOUT / LED_DATA via
pair to the east - which is why every phase-4 / knit_* strategy failed: they
all look for a path on the island's own layer or a single via onto opposite-
layer main fill, and neither exists here.

B.Cu in this pocket is all vertical bus lanes (COL5 at x=20.047, ENC2_A at
x=21.375) with a clear corridor between them. So: via down inside the island,
short B.Cu run south past the +3V3 fence, via back up into the main F.Cu pour.
Both endpoints and the run are clearance-checked; the corridor is searched if
the nominal position is blocked.

Run with KiCad python:  .../python3 v4/tools/fix_gnd_island.py [board.kicad_pcb]
"""
import ast
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "ClaudeMicroV4.kicad_pcb")

src = open(os.path.join(HERE, "finish_v4.py")).read()
tree = ast.parse(src)
keep = []
WANT_ASSIGN = {"mm", "W", "H", "HOLES", "POWER_NETS", "POUR_NETS", "VIA_D",
               "VIA_DRILL", "VR", "NO_VIA_RECTS", "VSYS_POLY", "KICAD_CLI"}
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Import,
                         ast.ImportFrom)):
        keep.append(node)
    elif isinstance(node, ast.Assign):
        tgts = []
        for t in node.targets:
            if isinstance(t, ast.Name):
                tgts.append(t.id)
            elif isinstance(t, ast.Tuple):
                tgts += [e.id for e in t.elts if isinstance(e, ast.Name)]
        if any(t in WANT_ASSIGN for t in tgts):
            keep.append(node)
ns = {"__name__": "finish_v4_lib"}
exec(compile(ast.Module(body=keep, type_ignores=[]), "finish_v4.py", "exec"), ns)

build_model = ns["build_model"]
seg_clear = ns["seg_clear"]
via_clear = ns["via_clear"]
add_track = ns["add_track"]
add_via = ns["add_via"]
save = ns["save"]
pour_clusters = ns["pour_clusters"]
mm = pcbnew.FromMM

# island (start) band and main-pour (end) band, both on F.Cu
X_CANDS = [20.70, 20.66, 20.74, 20.62, 20.78, 20.58]
Y_START = [20.20, 20.40, 20.00, 20.60]
Y_END = [23.00, 23.30, 22.70, 23.60, 24.00]

b = pcbnew.LoadBoard(BOARD)
net = b.FindNet("GND")
nc = net.GetNetCode()
model = build_model(b)


def inside(ch, x, y):
    return ch.PointInside(pcbnew.VECTOR2I(mm(x), mm(y)))


clusters = pour_clusters(b, "GND")
main_f = [ch for ch, lay in clusters[0]["islands"] if lay == pcbnew.F_Cu]
isl_f = []
for cl in clusters[1:]:
    isl_f += [ch for ch, lay in cl["islands"] if lay == pcbnew.F_Cu]

if not isl_f:
    print("no stranded GND island - nothing to do")
    raise SystemExit(0)

placed = None
for x in X_CANDS:
    for y1 in Y_START:
        if not any(inside(ch, x, y1) for ch in isl_f):
            continue
        if not via_clear(model, mm(x), mm(y1), nc, m=mm(0.18)):
            continue
        for y2 in Y_END:
            if not any(inside(ch, x, y2) for ch in main_f):
                continue
            if not via_clear(model, mm(x), mm(y2), nc, m=mm(0.18)):
                continue
            if not seg_clear(model, mm(x), mm(y1), mm(x), mm(y2),
                             pcbnew.B_Cu, nc, mm(0.125), m=mm(0.18)):
                continue
            placed = (x, y1, y2)
            break
        if placed:
            break
    if placed:
        break

if not placed:
    print("no clear jumper corridor found")
    raise SystemExit(1)

x, y1, y2 = placed
add_via(b, model, mm(x), mm(y1), net)
add_track(b, model, mm(x), mm(y1), mm(x), mm(y2), pcbnew.B_Cu, net, mm(0.25))
add_via(b, model, mm(x), mm(y2), net)
print(f"jumper: via ({x},{y1}) -> B.Cu -> via ({x},{y2})")
save(b)
print("saved")

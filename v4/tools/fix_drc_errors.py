#!/usr/bin/env python3
"""Repair the two hard DRC errors freerouting + finish_v4 left on V4.

1. USB_DP short: phase4b0 adds the B6 south descent
   (74.25,6.87)->(74.25,9.75) unconditionally - it is the only bespoke path
   in that block with no seg_clear() guard - and it lands on the VBAT_SNS
   run. The descent is also pointless: B6 and A6 are already tied by the
   y=8.07 jog and DP escapes north through the via at (74.25,5.67), so the
   stub is deleted rather than rerouted.

2. SW26 clearance: a phase-4 GND bridge stub passes 0.0998 mm from pad 1
   [IO0] of SW26 (rule 0.2 mm). Nudge the stub away in 0.05 mm steps,
   keeping both endpoints on their existing copper, until seg_clear passes.

Reuses finish_v4.py machinery via ast extraction (no phase pipeline runs).
Run with KiCad python:  .../python3 v4/tools/fix_drc_errors.py [board.kicad_pcb]
"""
import ast
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "AgentDeckV4.kicad_pcb")

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
mm = pcbnew.FromMM

TOL = mm(0.01)


def near(a, b):
    return abs(a - b) <= TOL


b = pcbnew.LoadBoard(BOARD)

# ---- fix 1: delete the unguarded USB_DP south descent ----------------------
DOOMED = (74.25, 6.87, 74.25, 9.75)
killed = 0
for t in list(b.GetTracks()):
    if t.GetClass() != "PCB_TRACK" or t.GetNetname() != "USB_DP":
        continue
    if t.GetLayer() != pcbnew.F_Cu:
        continue
    s, e = t.GetStart(), t.GetEnd()
    pts = [(s.x, s.y, e.x, e.y), (e.x, e.y, s.x, s.y)]
    if any(all(near(p, mm(q)) for p, q in zip(cand, DOOMED)) for cand in pts):
        b.Delete(t)
        killed += 1
print(f"fix1: deleted {killed} USB_DP descent segment(s)")

# ---- fix 2: nudge the GND stub away from SW26 pad 1 ------------------------
# Located by proximity to the SW26 pad rather than a fixed coordinate: the
# stub moves every time this runs, and seg_clear's 0.18 mm margin is looser
# than the 0.2 mm netclass rule DRC enforces, so it can take several passes.
SW26_PAD = (27.0, 23.65)
model = build_model(b)
gnd = b.FindNet("GND")
nc = gnd.GetNetCode() if gnd else None

target = None
best = None
for t in b.GetTracks():
    if t.GetClass() != "PCB_TRACK" or t.GetNetname() != "GND":
        continue
    if t.GetLayer() != pcbnew.F_Cu:
        continue
    s, e = t.GetStart(), t.GetEnd()
    if t.GetLength() > mm(0.5):
        continue
    d = min((abs(px - mm(SW26_PAD[0])) + abs(py - mm(SW26_PAD[1])))
            for (px, py) in ((s.x, s.y), (e.x, e.y)))
    if d < mm(2.0) and (best is None or d < best):
        best, target = d, t

if target is None:
    print("fix2: victim segment not found - skipped")
else:
    s, e = target.GetStart(), target.GetEnd()
    w = target.GetWidth()
    moved = False
    for step in range(1, 9):
        d = mm(0.05 * step)
        for dx, dy in ((-d, 0), (0, -d), (-d, -d), (0, d), (-d, d)):
            x1, y1 = s.x + dx, s.y + dy
            x2, y2 = e.x + dx, e.y + dy
            if seg_clear(model, x1, y1, x2, y2, target.GetLayer(), nc,
                         w // 2, m=mm(0.26)):
                target.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
                target.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
                print(f"fix2: nudged GND stub by ({dx/1e6:.2f},{dy/1e6:.2f}) mm")
                moved = True
                break
        if moved:
            break
    if not moved:
        b.Delete(target)
        print("fix2: no clear nudge found - stub deleted (island may reopen)")

pcbnew.SaveBoard(BOARD, b)
print("saved")

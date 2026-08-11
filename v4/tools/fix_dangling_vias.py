"""Remove VSYS_SW stitching vias that connect nothing.

All 37 via_dangling warnings are VSYS_SW: the stitcher dropped vias where the
opposite layer has no VSYS_SW fill, so each is a drill hit that joins pour to
nothing.

A via is only removed when NO track endpoint lands on it. That guard matters -
the via at (127.55, 13.0) is the one knit_maze placed to rescue cluster C6.1,
and it is a track endpoint, so it stays. Cluster counts are printed before and
after; DRC is the real gate.

Run with KiCad python:  .../python3 v4/tools/fix_dangling_vias.py [board]
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
pour_clusters = ns["pour_clusters"]

TOL = pcbnew.FromMM(0.02)
NET = "VSYS_SW"

b = pcbnew.LoadBoard(BOARD)
print("before:", {n: len(pour_clusters(b, n)) for n in ("GND", NET)})

ends = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.GetNetname() == NET:
        ends.append(t.GetStart())
        ends.append(t.GetEnd())

killed = kept = 0
for t in list(b.GetTracks()):
    if t.GetClass() != "PCB_VIA" or t.GetNetname() != NET:
        continue
    v = t.GetPosition()
    anchored = any(abs(v.x - e.x) <= TOL and abs(v.y - e.y) <= TOL
                   for e in ends)
    if anchored:
        kept += 1
        continue
    b.Delete(t)
    killed += 1

print(f"removed {killed} unanchored {NET} via(s); kept {kept} anchored")
if killed:
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    print("after:", {n: len(pour_clusters(b, n)) for n in ("GND", NET)})
    pcbnew.SaveBoard(BOARD, b)
    print("saved")

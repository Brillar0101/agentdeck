#!/usr/bin/env python3
"""Report why the C3-pad-2 GND island is stranded, and where the nearest
main-cluster GND copper actually is on each layer.

Diagnostic only - writes nothing. Run with KiCad python.
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
L = {pcbnew.F_Cu: "F", pcbnew.B_Cu: "B"}

b = pcbnew.LoadBoard(BOARD)
clusters = pour_clusters(b, "GND")
print(f"GND clusters: {len(clusters)}")
for i, cl in enumerate(clusters):
    tag = "MAIN" if i == 0 else f"C{i}"
    for ch, lay in cl["islands"]:
        bb = ch.BBox()
        print(f"  {tag:5s} {L.get(lay, lay)} "
              f"x {bb.GetLeft()/1e6:8.3f}..{bb.GetRight()/1e6:8.3f}  "
              f"y {bb.GetTop()/1e6:8.3f}..{bb.GetBottom()/1e6:8.3f}  "
              f"area {ch.Area()/1e12:8.3f} mm2")

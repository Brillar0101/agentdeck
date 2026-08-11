#!/usr/bin/env python3
"""Surgical pour-knit for the last clusters phase 4 / knit_extra left behind.

- Clusters whose only members are stitch vias (no pads): delete the vias and
  suppress the islands (pure pour slivers, nothing electrical lost).
- Clusters with pads: corridor-route (0.3/0.25/0.2 mm) from cluster points to
  interior points of the MAIN cluster's fill within 20 mm.

Reuses finish_v4.py machinery via ast extraction (no phase pipeline runs).
Run with KiCad python:  .../python3 v4/tools/knit_surgical.py
"""
import ast
import math
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BOARD = os.path.join(HW, "AgentDeckV4.kicad_pcb")

src = open(os.path.join(HERE, "finish_v4.py")).read()
tree = ast.parse(src)
WANT = {"mm", "W", "H", "HOLES", "POWER_NETS", "POUR_NETS", "VIA_D",
        "VIA_DRILL", "VR", "NO_VIA_RECTS", "VSYS_POLY", "KICAD_CLI"}
keep = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Import,
                         ast.ImportFrom)):
        keep.append(node)
    elif isinstance(node, ast.Assign):
        t = []
        for x in node.targets:
            if isinstance(x, ast.Name):
                t.append(x.id)
            elif isinstance(x, ast.Tuple):
                t += [e.id for e in x.elts if isinstance(e, ast.Name)]
        if any(k in WANT for k in t):
            keep.append(node)
ns = {"__name__": "lib"}
exec(compile(ast.Module(body=keep, type_ignores=[]), "finish_v4_lib", "exec"), ns)
pour_clusters = ns["pour_clusters"]
build_model = ns["build_model"]
try_corridor = ns["try_corridor"]
interior_points = ns["interior_points"]
suppress_island = ns["suppress_island"]
mm = pcbnew.FromMM


def run_round(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    model = build_model(b)
    fixed = failed = 0
    for net_name in ("GND", "VSYS_SW"):
        clusters = pour_clusters(b, net_name)
        if len(clusters) <= 1:
            continue
        net = b.FindNet(net_name)
        nc = net.GetNetCode()
        main = clusters[0]
        for cl in clusters[1:]:
            # does the cluster hold any real pad (footprint pad of this net)?
            pad_pts = []
            for (x, y, onf, onb) in cl["pts"]:
                for f in b.GetFootprints():
                    for p in f.Pads():
                        if p.GetNetCode() == nc and \
                                abs(p.GetPosition().x - x) < mm(0.05) and \
                                abs(p.GetPosition().y - y) < mm(0.05):
                            pad_pts.append((x, y, f.IsFlipped()))
            if not pad_pts:
                # orphan stitch vias + slivers: delete vias, suppress islands
                nkill = 0
                for (x, y, onf, onb) in cl["pts"]:
                    for t in list(b.GetTracks()):
                        if t.GetClass() == "PCB_VIA" and t.GetNetCode() == nc \
                                and abs(t.GetPosition().x - x) < mm(0.05) \
                                and abs(t.GetPosition().y - y) < mm(0.05) \
                                and not t.IsLocked():
                            b.Delete(t)
                            nkill += 1
                for ch, L in cl["islands"]:
                    suppress_island(b, ch, L)
                print(f"  {net_name}: orphan cluster pruned "
                      f"({nkill} vias, {len(cl['islands'])} islands)")
                fixed += 1
                continue
            # pad-bearing: corridor to main fill interior near the cluster
            cx = sum(x for x, y, _ in pad_pts) / len(pad_pts)
            cy = sum(y for x, y, _ in pad_pts) / len(pad_pts)
            srcs = []
            for (x, y, onf, onb) in cl["pts"]:
                srcs.append((x, y, pcbnew.F_Cu if onf else pcbnew.B_Cu))
            for ch, L in cl["islands"]:
                for (x, y) in interior_points(ch, 0.5):
                    srcs.append((x, y, L))
            dsts = []
            lim = mm(20)
            for ch, L in main["islands"]:
                bx = ch.BBox()
                if bx.GetLeft() - lim > cx or bx.GetRight() + lim < cx or \
                        bx.GetTop() - lim > cy or bx.GetBottom() + lim < cy:
                    continue
                for (x, y) in interior_points(ch, 1.2):
                    if abs(x - cx) < lim and abs(y - cy) < lim:
                        dsts.append((x, y, L))
            pairs = []
            for (x, y, L) in srcs:
                for (tx, ty, TL) in dsts:
                    pairs.append(((x - tx) ** 2 + (y - ty) ** 2,
                                  (x, y, L), (tx, ty, TL)))
            pairs.sort(key=lambda e: e[0])
            done = False
            for _, (x, y, L), (tx, ty, TL) in pairs[:600]:
                for w in (0.3, 0.25, 0.2):
                    res = try_corridor(b, model, net, (x, y), (tx, ty),
                                       L, TL, w)
                    if res:
                        print(f"  {net_name} bridge ({round(x/1e6,1)},"
                              f"{round(y/1e6,1)})->({round(tx/1e6,1)},"
                              f"{round(ty/1e6,1)}) w={w}: {res}")
                        done = True
                        break
                if done:
                    break
            if done:
                fixed += 1
            else:
                print(f"  {net_name} cluster at ({round(cx/1e6,1)},"
                      f"{round(cy/1e6,1)}): STILL FAILED")
                failed += 1
    return fixed, failed


for rnd in range(4):
    b = pcbnew.LoadBoard(BOARD)
    fx, fl = run_round(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print(f"knit_surgical[{rnd}]: fixed {fx}, failed {fl}")
    if fx == 0:
        break

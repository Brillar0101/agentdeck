#!/usr/bin/env python3
"""Targeted pour-knit pass for the clusters finish_v4's phase 4 could not
bridge at 0.5 mm: retry with 0.3/0.25 mm corridors and a deeper candidate
scan. Reuses finish_v4.py's geometry machinery (extracted via ast so the
phase pipeline does not execute).

Run with KiCad python:  .../python3 v4/tools/knit_extra.py [board.kicad_pcb]
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
pour_clusters = ns["pour_clusters"]
try_corridor = ns["try_corridor"]
interior_points = ns["interior_points"]
suppress_island = ns["suppress_island"]
via_clear = ns["via_clear"]
add_via = ns["add_via"]
mm = pcbnew.FromMM


def knit_thin(b, model, net_name):
    clusters = pour_clusters(b, net_name)
    if len(clusters) <= 1:
        return 0, 0
    net = b.FindNet(net_name)
    nc = net.GetNetCode()
    main = clusters[0]
    main_boxes = [(ch, ch.BBox(), L) for ch, L in main["islands"]]
    fixed = failed = 0
    for cl in clusters[1:]:
        done = False
        for ch, L in cl["islands"]:
            other = pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu
            mains = [(mch, mbx) for (mch, mbx, mL) in main_boxes if mL == other]
            for (x, y) in interior_points(ch, 0.6):
                for mch, mbx in mains:
                    if not (mbx.GetLeft() <= x <= mbx.GetRight()
                            and mbx.GetTop() <= y <= mbx.GetBottom()):
                        continue
                    if mch.PointInside(pcbnew.VECTOR2I(int(x), int(y))) \
                            and via_clear(model, x, y, nc):
                        add_via(b, model, x, y, net)
                        print(f"  {net_name} island via at "
                              f"({round(x/1e6,1)},{round(y/1e6,1)})")
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            cand_src = []
            for (x, y, onf, onb) in cl["pts"]:
                cand_src.append((x, y, pcbnew.F_Cu if onf else pcbnew.B_Cu))
            for ch, L in cl["islands"]:
                for (x, y) in interior_points(ch, 0.8):
                    cand_src.append((x, y, L))
            cand_dst = [(x, y) for (x, y, _, _) in main["pts"]][:800]
            best = []
            for (x, y, L) in cand_src:
                for (tx, ty) in cand_dst:
                    best.append(((x - tx) ** 2 + (y - ty) ** 2,
                                 (x, y, L), (tx, ty)))
            best.sort(key=lambda e: e[0])
            for _, (x, y, L), (tx, ty) in best[:200]:
                res = None
                for w in (0.3, 0.25):
                    res = try_corridor(b, model, net, (x, y), (tx, ty),
                                       L, pcbnew.F_Cu, w)
                    if not res:
                        res = try_corridor(b, model, net, (x, y), (tx, ty),
                                           L, pcbnew.B_Cu, w)
                    if res:
                        break
                if res:
                    print(f"  {net_name} thin bridge ({round(x/1e6,1)},"
                          f"{round(y/1e6,1)})->({round(tx/1e6,1)},"
                          f"{round(ty/1e6,1)}): {res}")
                    done = True
                    break
        if done:
            fixed += 1
            continue
        if not cl["pts"] and cl["islands"]:
            for ch, L in cl["islands"]:
                suppress_island(b, ch, L)
            print(f"  {net_name} empty island suppressed")
            fixed += 1
            continue
        where = (cl["islands"][0][0].BBox().Centre() if cl["islands"]
                 else pcbnew.VECTOR2I(int(cl["pts"][0][0]),
                                      int(cl["pts"][0][1])))
        print(f"  {net_name} cluster at ({round(where.x/1e6,1)},"
              f"{round(where.y/1e6,1)}): FAILED")
        failed += 1
    return fixed, failed


for rnd in range(6):
    b = pcbnew.LoadBoard(BOARD)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    model = build_model(b)
    total_fix = total_fail = 0
    for nname in ("GND", "VSYS_SW"):
        fx, fl = knit_thin(b, model, nname)
        total_fix += fx
        total_fail += fl
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print(f"knit_extra[{rnd}]: bridged {total_fix}, failed {total_fail}")
    if total_fix == 0:
        break

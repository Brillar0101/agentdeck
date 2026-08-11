#!/usr/bin/env python3
"""Final pour-knit pass: reconnect the last pad-bearing pour islands and prune
genuinely empty ones. Fast by construction — destinations are restricted to the
main cluster's pads/vias (small list) instead of every interior fill point,
which is what made the generic phase-4 scan intractable here.

Per non-main cluster of GND / VSYS_SW:
  1. no footprint pad inside  -> delete its orphan stitch vias and suppress the
     island with a no-pour rule area (pure pour sliver, nothing electrical).
  2. pad-bearing -> (a) try a via at small offsets around the pad that lands on
     main-cluster fill of the opposite layer; (b) else Z-route (0.3/0.25/0.2 mm)
     from the pad to the nearest main-cluster pads/vias.

Reuses finish_v4.py's geometry machinery via ast extraction, so importing it
does not re-run the phase pipeline.

Run with KiCad python:  .../python3 v4/tools/knit_final.py [board.kicad_pcb]
"""
import ast
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "ClaudeMicroV4.kicad_pcb")

_src = open(os.path.join(HERE, "finish_v4.py")).read()
_tree = ast.parse(_src)
_WANT = {"mm", "W", "H", "HOLES", "POWER_NETS", "POUR_NETS", "VIA_D",
         "VIA_DRILL", "VR", "NO_VIA_RECTS", "VSYS_POLY", "KICAD_CLI"}
_keep = []
for _n in _tree.body:
    if isinstance(_n, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
        _keep.append(_n)
    elif isinstance(_n, ast.Assign):
        _t = []
        for _x in _n.targets:
            if isinstance(_x, ast.Name):
                _t.append(_x.id)
            elif isinstance(_x, ast.Tuple):
                _t += [e.id for e in _x.elts if isinstance(e, ast.Name)]
        if any(k in _WANT for k in _t):
            _keep.append(_n)
_ns = {"__name__": "finish_v4_lib"}
exec(compile(ast.Module(body=_keep, type_ignores=[]), "finish_v4_lib", "exec"), _ns)

pour_clusters = _ns["pour_clusters"]
build_model = _ns["build_model"]
try_corridor = _ns["try_corridor"]
suppress_island = _ns["suppress_island"]
via_clear = _ns["via_clear"]
add_via = _ns["add_via"]
mm = pcbnew.FromMM


def pad_index(b, nc):
    """{(x_um, y_um): (footprint, pad)} for every pad on this net."""
    out = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == nc:
                pos = p.GetPosition()
                out[(round(pos.x / 1000), round(pos.y / 1000))] = (f, p)
    return out


def main_anchors(b, main, nc, cx, cy, limit_mm=25.0, cap=120):
    """Main-cluster pads/vias nearest (cx, cy), as (x, y, layer)."""
    cand = []
    lim = mm(limit_mm)
    for (x, y, onf, onb) in main["pts"]:
        if abs(x - cx) > lim or abs(y - cy) > lim:
            continue
        if onf:
            cand.append((x, y, pcbnew.F_Cu))
        if onb:
            cand.append((x, y, pcbnew.B_Cu))
    cand.sort(key=lambda e: (e[0] - cx) ** 2 + (e[1] - cy) ** 2)
    return cand[:cap]


def main_fill(main):
    return [(ch, ch.BBox(), L) for ch, L in main["islands"]]


def run_round(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    model = build_model(b)
    fixed = failed = 0
    for net_name in ("GND", "VSYS_SW"):
        net = b.FindNet(net_name)
        if net is None:
            continue
        nc = net.GetNetCode()
        clusters = pour_clusters(b, net_name)
        if len(clusters) <= 1:
            continue
        main = clusters[0]
        mfill = main_fill(main)
        pads = pad_index(b, nc)
        for cl in clusters[1:]:
            members = []
            for (x, y, onf, onb) in cl["pts"]:
                hit = pads.get((round(x / 1000), round(y / 1000)))
                if hit:
                    members.append((x, y, hit))
            if not members:
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
                print(f"  {net_name}: orphan sliver pruned "
                      f"({nkill} vias, {len(cl['islands'])} islands)")
                fixed += 1
                continue

            px, py, (fp, pad) = members[0]
            name = f"{fp.GetReference()}.{pad.GetNumber()}"
            pad_layer = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
            done = False

            # (a) via near the pad landing on main fill of the opposite layer
            other = pcbnew.B_Cu if pad_layer == pcbnew.F_Cu else pcbnew.F_Cu
            mains = [(ch, bx) for (ch, bx, L) in mfill if L == other]
            for r in (0.0, 0.55, 0.75, 0.95, 1.2, 1.5, 1.85, 2.2):
                for a in range(0, 360, 10 if r else 360):
                    vx = px + mm(r) * math.cos(math.radians(a))
                    vy = py + mm(r) * math.sin(math.radians(a))
                    inside = False
                    for ch, bx in mains:
                        if bx.GetLeft() <= vx <= bx.GetRight() and \
                                bx.GetTop() <= vy <= bx.GetBottom() and \
                                ch.PointInside(pcbnew.VECTOR2I(int(vx), int(vy))):
                            inside = True
                            break
                    if not inside or not via_clear(model, vx, vy, nc):
                        continue
                    if r and not _ns["seg_clear"](model, px, py, vx, vy,
                                                 pad_layer, nc, mm(0.1)):
                        continue
                    if r:
                        _ns["add_track"](b, model, px, py, vx, vy, pad_layer,
                                         net, mm(0.2))
                    add_via(b, model, vx, vy, net)
                    print(f"  {net_name} {name}: via at "
                          f"({round(vx/1e6,2)},{round(vy/1e6,2)}) r={r}")
                    done = True
                    break
                if done:
                    break

            # (b) Z-route to nearest main-cluster anchors
            if not done:
                for (tx, ty, TL) in main_anchors(b, main, nc, px, py):
                    for w in (0.3, 0.25, 0.2):
                        res = try_corridor(b, model, net, (px, py), (tx, ty),
                                           pad_layer, TL, w)
                        if res:
                            print(f"  {net_name} {name}: bridge -> "
                                  f"({round(tx/1e6,2)},{round(ty/1e6,2)}) "
                                  f"w={w}: {res}")
                            done = True
                            break
                    if done:
                        break

            # (c) Z-route to a via-able point that sits ON main-cluster fill.
            # The corridor ends inside the main pour, so same-layer arrival
            # merges with the fill; a differing layer gets a via from
            # try_corridor itself.
            if not done:
                lands = []
                for r in [x * 0.25 for x in range(4, 25)]:
                    for a in range(0, 360, 8):
                        vx = px + mm(r) * math.cos(math.radians(a))
                        vy = py + mm(r) * math.sin(math.radians(a))
                        if not via_clear(model, vx, vy, nc):
                            continue
                        for ch, bx, L in mfill:
                            if bx.GetLeft() <= vx <= bx.GetRight() and \
                                    bx.GetTop() <= vy <= bx.GetBottom() and \
                                    ch.PointInside(pcbnew.VECTOR2I(int(vx),
                                                                   int(vy))):
                                lands.append((r, vx, vy, L))
                                break
                lands.sort(key=lambda e: e[0])
                for (r, tx, ty, TL) in lands[:80]:
                    for w in (0.3, 0.25, 0.2):
                        res = try_corridor(b, model, net, (px, py), (tx, ty),
                                           pad_layer, TL, w)
                        if res:
                            print(f"  {net_name} {name}: fill-land -> "
                                  f"({round(tx/1e6,2)},{round(ty/1e6,2)}) "
                                  f"{'F' if TL == pcbnew.F_Cu else 'B'} "
                                  f"r={round(r,2)} w={w}: {res}")
                            done = True
                            break
                    if done:
                        break

            if done:
                fixed += 1
            else:
                print(f"  {net_name} {name} at ({round(px/1e6,2)},"
                      f"{round(py/1e6,2)}): FAILED")
                failed += 1
    return fixed, failed


for rnd in range(6):
    b = pcbnew.LoadBoard(BOARD)
    fx, fl = run_round(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print(f"knit_final[{rnd}]: fixed {fx}, failed {fl}")
    if fx == 0:
        break

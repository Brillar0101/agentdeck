#!/usr/bin/env python3
"""Maze-router knit for pour-island pads the Z-corridor router cannot reach.

The generic phase-4/knit_final bridges are 2-segment Z paths; in the dense
U1/U2 pocket of this board no Z fits, but an L/S path with a layer change does.
This tool runs a small A* over a 0.125 mm grid on both copper layers inside a
window around the stranded pad, using finish_v4.py's own clearance model as the
obstacle test, and stops as soon as it reaches main-cluster pour fill (arriving
on the fill's own layer merges with it) or a main-cluster pad/via.

Run with KiCad python:  .../python3 v4/tools/knit_maze.py [board.kicad_pcb]
"""
import ast
import heapq
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "AgentDeckV4.kicad_pcb")

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
seg_clear = _ns["seg_clear"]
via_clear = _ns["via_clear"]
add_track = _ns["add_track"]
add_via = _ns["add_via"]
suppress_island = _ns["suppress_island"]
mm = pcbnew.FromMM

STEP = mm(0.125)          # routing grid
WIN = 9.0                 # mm half-window around the stranded pad
TW = 0.2                  # track width mm
VIA_COST = 6              # in grid steps
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


def pad_index(b, nc):
    out = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == nc:
                pos = p.GetPosition()
                out[(round(pos.x / 1000), round(pos.y / 1000))] = (f, p)
    return out


def route_one(b, model, net, px, py, pad_layer, main):
    """A* from (px, py, pad_layer) to main-cluster fill/pads. Returns path or
    None; path = [(x, y, layer), ...] with layer changes marked by repeats."""
    nc = net.GetNetCode()
    half = mm(TW / 2)
    fill = [(ch, ch.BBox(), L) for ch, L in main["islands"]]
    anchors = set()
    for (x, y, onf, onb) in main["pts"]:
        if abs(x - px) < mm(WIN) and abs(y - py) < mm(WIN):
            if onf:
                anchors.add((round(x / STEP), round(y / STEP), pcbnew.F_Cu))
            if onb:
                anchors.add((round(x / STEP), round(y / STEP), pcbnew.B_Cu))

    def on_fill(x, y, L):
        for ch, bx, FL in fill:
            if FL != L:
                continue
            if bx.GetLeft() <= x <= bx.GetRight() and \
                    bx.GetTop() <= y <= bx.GetBottom() and \
                    ch.PointInside(pcbnew.VECTOR2I(int(x), int(y))):
                return True
        return False

    def is_goal(ix, iy, L):
        if (ix, iy, L) in anchors:
            return True
        return on_fill(ix * STEP, iy * STEP, L)

    sx, sy = round(px / STEP), round(py / STEP)
    lo_x, hi_x = round((px - mm(WIN)) / STEP), round((px + mm(WIN)) / STEP)
    lo_y, hi_y = round((py - mm(WIN)) / STEP), round((py + mm(WIN)) / STEP)
    start = (sx, sy, pad_layer)
    seen = {start: 0}
    prev = {}
    pq = [(0, 0, start)]
    NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    goal = None
    guard = 0
    while pq and guard < 250000:
        guard += 1
        _, g, cur = heapq.heappop(pq)
        if g > seen.get(cur, 1 << 30):
            continue
        ix, iy, L = cur
        if cur != start and is_goal(ix, iy, L):
            goal = cur
            break
        for dx, dy in NB:
            nx, ny = ix + dx, iy + dy
            if not (lo_x <= nx <= hi_x and lo_y <= ny <= hi_y):
                continue
            if not seg_clear(model, ix * STEP, iy * STEP, nx * STEP, ny * STEP,
                             L, nc, half, m=mm(0.2)):
                continue
            cost = g + (14 if dx and dy else 10)
            nxt = (nx, ny, L)
            if cost < seen.get(nxt, 1 << 30):
                seen[nxt] = cost
                prev[nxt] = cur
                heapq.heappush(pq, (cost, cost, nxt))
        # layer change
        oL = pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu
        if via_clear(model, ix * STEP, iy * STEP, nc, m=mm(0.2)):
            nxt = (ix, iy, oL)
            cost = g + VIA_COST * 10
            if cost < seen.get(nxt, 1 << 30):
                seen[nxt] = cost
                prev[nxt] = cur
                heapq.heappush(pq, (cost, cost, nxt))
    if goal is None:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return [(ix * STEP, iy * STEP, L) for ix, iy, L in path]


def emit(b, model, net, path):
    """Collapse collinear runs into tracks, place vias at layer changes."""
    segs, vias = [], []
    i = 0
    while i < len(path) - 1:
        x1, y1, l1 = path[i]
        x2, y2, l2 = path[i + 1]
        if l1 != l2:
            vias.append((x1, y1))
            i += 1
            continue
        # extend while direction and layer hold
        dx, dy = x2 - x1, y2 - y1
        j = i + 1
        while j < len(path) - 1:
            x3, y3, l3 = path[j]
            x4, y4, l4 = path[j + 1]
            if l3 != l4 or l4 != l1:
                break
            if (x4 - x3, y4 - y3) != (dx, dy):
                break
            j += 1
        xe, ye, _ = path[j]
        segs.append((x1, y1, xe, ye, l1))
        i = j
    for (x1, y1, x2, y2, L) in segs:
        if (x1, y1) != (x2, y2):
            add_track(b, model, x1, y1, x2, y2, L, net, mm(TW))
    for (x, y) in vias:
        add_via(b, model, x, y, net)
    return len(segs), len(vias)


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
                print(f"  {net_name}: orphan sliver pruned ({nkill} vias)")
                fixed += 1
                continue
            px, py, (fp, pad) = members[0]
            name = f"{fp.GetReference()}.{pad.GetNumber()}"
            pad_layer = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
            path = route_one(b, model, net, px, py, pad_layer, main)
            if path is None:
                print(f"  {net_name} {name}: MAZE FAILED")
                failed += 1
                continue
            ns_, nv = emit(b, model, net, path)
            ex, ey, eL = path[-1]
            print(f"  {net_name} {name}: maze {ns_} segs {nv} vias -> "
                  f"({round(ex/1e6,2)},{round(ey/1e6,2)})"
                  f"{'F' if eL == pcbnew.F_Cu else 'B'}")
            fixed += 1
    return fixed, failed


for rnd in range(6):
    b = pcbnew.LoadBoard(BOARD)
    fx, fl = run_round(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print(f"knit_maze[{rnd}]: fixed {fx}, failed {fl}")
    if fx == 0:
        break

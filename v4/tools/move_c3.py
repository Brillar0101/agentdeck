#!/usr/bin/env python3
"""Move C3 out of the column-bus fan-out so its GND pad reaches main pour.

C3 sat at (21.0, 21.0) inside the U1 column-bus escape, where its GND pad was
unreachable on both layers: F.Cu fenced by the +3V3 rail (removing either
segment merges the island, but the rail cannot be deleted - it splits +3V3 -
nor moved, since any C4->C3 path crosses the same corridor), and B.Cu shredded
into non-main slivers by seven bus lanes. Zero island points sit over main B
fill, so no via or jumper exists.

C3 is a bulk cap on the rail - U1's +3V3 pin is at (11.25, 2.28), ~20 mm away -
so relocating it costs nothing electrically. It moves 3 mm south into the open
main pour; the pour grounds pad 2 directly. The old C2<->C4 +3V3 path stays
intact (its stub and diagonal still meet at (21.0, 21.775)); pad 1 is re-fed
with a tap off the C4 run.

Run with KiCad python:  .../python3 v4/tools/move_c3.py [board.kicad_pcb]
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
pour_clusters = ns["pour_clusters"]
mm = pcbnew.FromMM

FEED_W = 0.35                 # match the C4 run
FEED_TAPS = (24.0, 23.5, 24.5, 23.0, 25.0)
# 3.0 mm put pad 1 within 0.134 mm of the IO0 run at y=25.46, so the shift is
# searched rather than assumed - and the pads themselves are clearance-checked,
# not just the feed track.
# C3 has to clear the +3V3 run at y=22.55 on the way south without reaching the
# IO0 run at y=25.46 - a window of roughly 0.05 mm, so the candidates are fine.
# With the corrected corner reach (0.854 mm incl. clearance) there is no
# vertical-only answer: clearing the +3V3 diagonal wants dy >= ~2.98, clearing
# the IO0 run wants dy <= ~2.73. Going west escapes the 45-degree diagonal, so
# the search is 2D.
DY_CANDS = (2.6, 2.7, 2.5, 2.8, 2.4, 2.3)
DX_CANDS = (-0.8, -1.0, -0.6, -1.2, -0.4, 0.0)


seg_pt_dist = ns["seg_pt_dist"]


def pads_clear(bd, fp, clr=mm(0.2)):
    """Clearance of the moved pads against foreign-net tracks and pads.

    Deliberately does NOT use the finish_v4 model: the zones are still filled
    for C3's OLD position, so pour copper covers the candidate location and
    every position reads as blocked. Pads and tracks are the real constraint;
    the pour re-carves itself on refill.
    """
    for p in fp.Pads():
        pos = p.GetPosition()
        sz = p.GetSize()
        # diagonal half-extent, not max(w,h)/2: a rectangular pad reaches
        # further at its corners, and the circular approximation let the +3V3
        # diagonal end up 0.13 mm from the GND pad corner
        reach = int(((sz.x / 2) ** 2 + (sz.y / 2) ** 2) ** 0.5) + clr
        pn = p.GetNetname()
        for t in bd.GetTracks():
            if t.GetNetname() == pn:
                continue
            if t.GetClass() == "PCB_VIA":
                d = ((t.GetPosition().x - pos.x) ** 2
                     + (t.GetPosition().y - pos.y) ** 2) ** 0.5
                d -= t.GetWidth() / 2
            else:
                # SMD pads are single-layer: a B.Cu bus lane under the pad is
                # not a conflict, and treating it as one rejects every position
                if not p.IsOnLayer(t.GetLayer()):
                    continue
                s, e = t.GetStart(), t.GetEnd()
                d = seg_pt_dist(s.x, s.y, e.x, e.y, pos.x, pos.y)
                d -= t.GetWidth() / 2
            if d < reach:
                return False, f"{pn} pad vs {t.GetNetname()} ({d/1e6:.3f} mm)"
        for ofp in bd.GetFootprints():
            if ofp.GetReference() == fp.GetReference():
                continue
            for op in ofp.Pads():
                if op.GetNetname() == pn:
                    continue
                d = ((op.GetPosition().x - pos.x) ** 2
                     + (op.GetPosition().y - pos.y) ** 2) ** 0.5
                d -= max(op.GetSize().x, op.GetSize().y) / 2
                if d < reach:
                    return False, (f"{pn} pad vs {ofp.GetReference()}"
                                   f" ({d/1e6:.3f} mm)")
    return True, ""


chosen = None
for dy, dx in [(y, x) for y in DY_CANDS for x in DX_CANDS]:
    b = pcbnew.LoadBoard(BOARD)
    c3 = None
    for fp in b.GetFootprints():
        if fp.GetReference() == "C3":
            c3 = fp
            break
    if c3 is None:
        raise SystemExit("C3 not found")
    c3.Move(pcbnew.VECTOR2I(mm(dx), mm(dy)))
    pad1 = {p.GetPadName(): p for p in c3.Pads()}["1"]
    px, py = pad1.GetPosition().x / 1e6, pad1.GetPosition().y / 1e6
    net = b.FindNet("+3V3")
    nc = net.GetNetCode()
    model = build_model(b)
    ok, why = pads_clear(b, c3)
    if not ok:
        print(f"dy={dy} dx={dx}: pads not clear - {why}")
        continue
    feed = None
    for tap in FEED_TAPS:
        segs = [(tap, 22.55, tap, py), (tap, py, px, py)]
        if all(seg_clear(model, mm(a), mm(bb), mm(c), mm(d), pcbnew.F_Cu, nc,
                         mm(FEED_W / 2), m=mm(0.18)) for a, bb, c, d in segs):
            feed = segs
            print(f"dy={dy} dx={dx}: pads clear, feed tap at x={tap}, "
                  f"pad1 at ({px:.3f},{py:.3f})")
            break
    if feed:
        chosen = (b, net, feed)
        break
    print(f"dy={dy} dx={dx}: no clear feed")

if chosen is None:
    raise SystemExit("no workable C3 position found")
b, net, feed = chosen

for a, bb, c, d in feed:
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(a), mm(bb)))
    t.SetEnd(pcbnew.VECTOR2I(mm(c), mm(d)))
    t.SetWidth(mm(FEED_W))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    b.Add(t)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
print("GND clusters:", len(pour_clusters(b, "GND")))
pcbnew.SaveBoard(BOARD, b)
print("saved")

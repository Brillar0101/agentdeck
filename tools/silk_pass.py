#!/usr/bin/env python3
"""Silkscreen cleanup pass.

Enforces the house silk rules on a board:
  * text >= 1.0 mm high, stroke = height/6, angle normalised to 0 or 90 deg
  * silk clipped 0.15 mm clear of every pad on the same side (ink on a pad
    stops solder wetting, and fabs clip it crudely if we do not)
  * silk kept 0.2 mm inside the board outline
  * silk kept off untented vias

Clipping works by sampling each segment and keeping the runs that no pad
claims, so it is shape-agnostic for pads (round, oval, roundrect, custom).
Rectangles are exploded into four segments first. Arcs, circles and polygons
are NOT clipped - they are reported for manual attention instead of being
silently approximated into polylines.

The font face cannot be set through the pcbnew API (SetFont exists but the
KIFONT_FONT binding does not), so faces are injected by fix_silk_font.py.

Run with KiCad python:  .../python3 tools/silk_pass.py <board.kicad_pcb>
"""
import os
import sys

import pcbnew

mm = pcbnew.FromMM

BOARD = sys.argv[1] if len(sys.argv) > 1 else None
if not BOARD or not os.path.exists(BOARD):
    raise SystemExit("usage: silk_pass.py <board.kicad_pcb>")

PAD_CLR = mm(0.15)
EDGE_CLR = mm(0.2)
MIN_H = mm(1.0)
STEP = mm(0.05)
MIN_KEEP = mm(0.3)      # shorter leftovers are visual noise, drop them

SILK = {pcbnew.F_SilkS: pcbnew.F_Cu, pcbnew.B_SilkS: pcbnew.B_Cu}

b = pcbnew.LoadBoard(BOARD)


# ---- pad / edge obstacle model --------------------------------------------
pads = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
for fp in b.GetFootprints():
    for p in fp.Pads():
        for silk, cu in SILK.items():
            if p.IsOnLayer(cu):
                pads[silk].append(p)

vias = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append((t.GetPosition(), t.GetWidth() // 2))

edge = b.GetBoardEdgesBoundingBox()


def blocked(pt, silk_layer):
    for p in pads[silk_layer]:
        if p.HitTest(pt, PAD_CLR):
            return True
    for (vp, vr) in vias:
        dx, dy = pt.x - vp.x, pt.y - vp.y
        if (dx * dx + dy * dy) ** 0.5 < vr + PAD_CLR:
            return True
    if not (edge.GetLeft() + EDGE_CLR < pt.x < edge.GetRight() - EDGE_CLR
            and edge.GetTop() + EDGE_CLR < pt.y < edge.GetBottom() - EDGE_CLR):
        return True
    return False


def clip_segment(x1, y1, x2, y2, silk_layer):
    """Return the sub-segments of (x1,y1)-(x2,y2) that no pad/via/edge claims."""
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if length == 0:
        return []
    n = max(2, int(length / STEP) + 1)
    runs, cur = [], None
    for i in range(n + 1):
        f = i / n
        pt = pcbnew.VECTOR2I(int(x1 + (x2 - x1) * f), int(y1 + (y2 - y1) * f))
        if blocked(pt, silk_layer):
            if cur:
                runs.append(cur)
                cur = None
        else:
            if cur is None:
                cur = [pt, pt]
            else:
                cur[1] = pt
    if cur:
        runs.append(cur)
    out = []
    for (a, c) in runs:
        if ((c.x - a.x) ** 2 + (c.y - a.y) ** 2) ** 0.5 >= MIN_KEEP:
            out.append((a, c))
    return out


def shape_segments(s):
    """Segments to clip for this shape, or None if the shape is left alone."""
    st = s.GetShape()
    if st == pcbnew.SHAPE_T_SEGMENT:
        a, c = s.GetStart(), s.GetEnd()
        return [(a.x, a.y, c.x, c.y)]
    if st in (pcbnew.SHAPE_T_RECT, pcbnew.SHAPE_T_RECTANGLE):
        a, c = s.GetStart(), s.GetEnd()
        x1, y1, x2, y2 = a.x, a.y, c.x, c.y
        return [(x1, y1, x2, y1), (x2, y1, x2, y2),
                (x2, y2, x1, y2), (x1, y2, x1, y1)]
    return None


def add_segment(parent, proto, a, c):
    s = pcbnew.PCB_SHAPE(parent)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(int(a.x), int(a.y)))
    s.SetEnd(pcbnew.VECTOR2I(int(c.x), int(c.y)))
    s.SetLayer(proto.GetLayer())
    s.SetWidth(proto.GetWidth())
    parent.Add(s)


# ---- pass 1: clip silk graphics -------------------------------------------
clipped = removed = untouched = skipped = 0
holders = [(fp, list(fp.GraphicalItems())) for fp in b.GetFootprints()]
holders.append((b, [d for d in b.GetDrawings()]))

for parent, items in holders:
    for s in items:
        if s.GetClass() != "PCB_SHAPE":
            continue
        lay = s.GetLayer()
        if lay not in SILK:
            continue
        segs = shape_segments(s)
        if segs is None:
            for (x1, y1, x2, y2) in []:
                pass
            skipped += 1
            continue
        kept = []
        changed = False
        for (x1, y1, x2, y2) in segs:
            runs = clip_segment(x1, y1, x2, y2, lay)
            whole = (len(runs) == 1
                     and abs(runs[0][0].x - x1) < STEP
                     and abs(runs[0][0].y - y1) < STEP
                     and abs(runs[0][1].x - x2) < STEP
                     and abs(runs[0][1].y - y2) < STEP)
            if not whole:
                changed = True
            kept += runs
        if not changed:
            untouched += 1
            continue
        for (a, c) in kept:
            add_segment(parent, s, a, c)
        parent.Remove(s)
        if kept:
            clipped += 1
        else:
            removed += 1

print(f"graphics: clipped {clipped}, fully removed {removed}, "
      f"untouched {untouched}, non-clippable (arc/circle/poly) {skipped}")


# ---- pass 2: text metrics --------------------------------------------------
def fix_text(t):
    hit = []
    h = t.GetTextHeight()
    if h < MIN_H:
        t.SetTextSize(pcbnew.VECTOR2I(MIN_H, MIN_H))
        h = MIN_H
        hit.append("height")
    want = int(h / 6)
    if abs(t.GetTextThickness() - want) > mm(0.01):
        t.SetTextThickness(want)
        hit.append("stroke")
    ang = t.GetTextAngle().AsDegrees() % 360
    norm = 0 if ang < 45 or ang >= 315 else (90 if ang < 135 else
                                             (0 if ang < 225 else 90))
    if abs(ang - norm) > 0.5:
        t.SetTextAngle(pcbnew.EDA_ANGLE(norm, pcbnew.DEGREES_T))
        hit.append(f"angle {ang:.0f}->{norm}")
    return hit


texts = 0
for d in b.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() in SILK:
        hits = fix_text(d)
        if hits:
            texts += 1
            print(f"  text {d.GetText()[:34]!r}: {', '.join(hits)}")
for fp in b.GetFootprints():
    for t in list(fp.GraphicalItems()) + [fp.Reference(), fp.Value()]:
        if t.GetClass() in ("PCB_TEXT", "PCB_FIELD") and t.GetLayer() in SILK \
                and t.IsVisible():
            if fix_text(t):
                texts += 1
print(f"text: adjusted {texts}")

pcbnew.SaveBoard(BOARD, b)
print("saved", BOARD)

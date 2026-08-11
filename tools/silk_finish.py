#!/usr/bin/env python3
"""Resolve the silk violations silk_pass.py deliberately left alone.

Three categories, three strategies:

  1. Free-standing board text sitting on copper -> search a nearby clear spot
     on a grid and move it, keeping the original position if nothing is free.
  2. Pin-1 marker circles overlapping their own pad -> walk the dot outward
     until it clears both the pad and the footprint outline. Circles are never
     approximated into polylines; they move intact.
  3. Footprint labels that overlap each other because the text is wider than
     the pad pitch (J2: "SWCLK" is 3.5 mm on a 2.54 mm pitch) -> rotate to
     90 deg, which is inside the two-orientation rule, and push clear of pads.

Run with KiCad python:  .../python3 tools/silk_finish.py <board.kicad_pcb>
"""
import math
import os
import sys

import pcbnew

mm = pcbnew.FromMM

BOARD = sys.argv[1] if len(sys.argv) > 1 else None
if not BOARD or not os.path.exists(BOARD):
    raise SystemExit("usage: silk_finish.py <board.kicad_pcb>")

PAD_CLR = mm(0.15)
SILK_GAP = mm(0.15)
SILK = {pcbnew.F_SilkS: pcbnew.F_Cu, pcbnew.B_SilkS: pcbnew.B_Cu}

b = pcbnew.LoadBoard(BOARD)

pads = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
for fp in b.GetFootprints():
    for p in fp.Pads():
        for silk, cu in SILK.items():
            if p.IsOnLayer(cu):
                pads[silk].append(p)


def box_hits_pad(box, layer):
    for p in pads[layer]:
        pb = p.GetBoundingBox()
        pb.Inflate(PAD_CLR)
        if box.Intersects(pb):
            return True
    return False


def silk_items(layer):
    out = []
    for d in b.GetDrawings():
        if d.GetLayer() == layer and d.GetClass() in ("PCB_TEXT", "PCB_SHAPE"):
            out.append(d)
    for fp in b.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetLayer() == layer:
                out.append(g)
    return out


def same_item(a, c):
    """Identity for board items.

    `a is c` does NOT work: SWIG builds a fresh Python proxy on every access,
    so the item being moved never excludes itself from its own obstacle list -
    it collides with itself at every candidate position and the search always
    reports failure. Compare the underlying pointers instead.
    """
    try:
        return a.this == c.this
    except AttributeError:
        return a is c


def _seg_pt(x1, y1, x2, y2, px, py):
    vx, vy = x2 - x1, y2 - y1
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L2))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


def _rect_seg_dist(box, x1, y1, x2, y2):
    """True distance from an axis-aligned box to a segment.

    Bounding-box overlap is useless here: a long diagonal silk segment has a
    huge bbox it barely occupies, so bbox tests either reject every candidate
    position or accept ones that really do collide.
    """
    L, T = box.GetLeft(), box.GetTop()
    R, B = box.GetRight(), box.GetBottom()
    if L <= x1 <= R and T <= y1 <= B:
        return 0.0
    if L <= x2 <= R and T <= y2 <= B:
        return 0.0
    edges = ((L, T, R, T), (R, T, R, B), (R, B, L, B), (L, B, L, T))
    best = min(_seg_pt(x1, y1, x2, y2, ex, ey) for (ex, ey, _, _) in edges)
    for (ax, ay, bx, by) in edges:
        best = min(best, _seg_pt(ax, ay, bx, by, x1, y1),
                   _seg_pt(ax, ay, bx, by, x2, y2))
    return best


def _item_clear(box, it, gap):
    if it.GetClass() == "PCB_SHAPE":
        st = it.GetShape()
        half = it.GetWidth() / 2
        if st == pcbnew.SHAPE_T_SEGMENT:
            s, e = it.GetStart(), it.GetEnd()
            return _rect_seg_dist(box, s.x, s.y, e.x, e.y) >= gap + half
        if st in (pcbnew.SHAPE_T_RECT, pcbnew.SHAPE_T_RECTANGLE):
            s, e = it.GetStart(), it.GetEnd()
            segs = ((s.x, s.y, e.x, s.y), (e.x, s.y, e.x, e.y),
                    (e.x, e.y, s.x, e.y), (s.x, e.y, s.x, s.y))
            return all(_rect_seg_dist(box, *sg) >= gap + half for sg in segs)
    ib = it.GetBoundingBox()
    ib.Inflate(gap)
    return not box.Intersects(ib)


_SILK_CACHE = {}


def box_hits_silk(box, layer, skip, only=None):
    """Silk-vs-silk test.

    `only` restricts the comparison to the specific items DRC complained
    about. Comparing against every silk item rejects every candidate on a
    board this dense - bounding boxes of nearby-but-not-touching graphics
    always intersect, which is what made the first run find nothing.
    """
    if only is not None:
        pool = only
    else:
        if layer not in _SILK_CACHE:
            _SILK_CACHE[layer] = silk_items(layer)
        pool = _SILK_CACHE[layer]
    for it in pool:
        if same_item(it, skip):
            continue
        if not _item_clear(box, it, SILK_GAP):
            return True
    return False


# ---- 1. free-standing board text -------------------------------------------
# Only the texts DRC actually names are candidates - my own predicate flagged
# every text on the board, including four DRC is happy with.
FLAGGED_TEXT = os.environ.get("SILK_TEXTS", "FLASH").split("|")

moved_text = 0
for d in list(b.GetDrawings()):
    if d.GetClass() != "PCB_TEXT" or d.GetLayer() not in SILK:
        continue
    if not any(f in d.GetText() for f in FLAGGED_TEXT):
        continue
    lay = d.GetLayer()
    if not box_hits_pad(d.GetBoundingBox(), lay):
        continue
    orig = d.GetPosition()
    best = None
    for r in range(1, 60):                      # expanding ring search
        step = mm(0.5) * r
        for ang in range(0, 360, 15):
            dx = int(step * math.cos(math.radians(ang)))
            dy = int(step * math.sin(math.radians(ang)))
            d.SetPosition(pcbnew.VECTOR2I(orig.x + dx, orig.y + dy))
            box = d.GetBoundingBox()
            if not box_hits_pad(box, lay) and not box_hits_silk(box, lay, d):
                best = (orig.x + dx, orig.y + dy)
                break
        if best:
            break
    if best:
        d.SetPosition(pcbnew.VECTOR2I(*best))
        print(f"  moved text {d.GetText()[:32]!r} to "
              f"({best[0]/1e6:.2f},{best[1]/1e6:.2f})")
        moved_text += 1
    else:
        d.SetPosition(orig)
        print(f"  text {d.GetText()[:32]!r}: no clear spot found - left put")
print(f"board text: moved {moved_text}")

# ---- 2. pin-1 marker circles ----------------------------------------------
moved_dots = 0
for fp in b.GetFootprints():
    for g in list(fp.GraphicalItems()):
        if g.GetClass() != "PCB_SHAPE" or g.GetLayer() not in SILK:
            continue
        if g.GetShape() != pcbnew.SHAPE_T_CIRCLE:
            continue
        lay = g.GetLayer()
        if not box_hits_pad(g.GetBoundingBox(), lay):
            continue
        c0 = g.GetStart()
        e0 = g.GetEnd()
        placed = None
        for r in range(1, 40):
            step = mm(0.05) * r
            for ang in range(0, 360, 15):
                dx = int(step * math.cos(math.radians(ang)))
                dy = int(step * math.sin(math.radians(ang)))
                g.SetStart(pcbnew.VECTOR2I(c0.x + dx, c0.y + dy))
                g.SetEnd(pcbnew.VECTOR2I(e0.x + dx, e0.y + dy))
                box = g.GetBoundingBox()
                own = [s for s in fp.GraphicalItems()
                       if not same_item(s, g) and s.GetLayer() == lay]
                if not box_hits_pad(box, lay) \
                        and not box_hits_silk(box, lay, g, only=own):
                    placed = (dx, dy)
                    break
            if placed:
                break
        if placed:
            print(f"  {fp.GetReference()} pin-1 dot moved "
                  f"({placed[0]/1e6:+.2f},{placed[1]/1e6:+.2f}) mm")
            moved_dots += 1
        else:
            g.SetStart(c0)
            g.SetEnd(e0)
            print(f"  {fp.GetReference()} pin-1 dot: no clear spot")
print(f"pin-1 dots: moved {moved_dots}")

# ---- 3. footprint labels wider than their pitch ----------------------------
fixed_lbl = 0
for fp in b.GetFootprints():
    texts = [g for g in fp.GraphicalItems()
             if g.GetClass() == "PCB_TEXT" and g.GetLayer() in SILK
             and g.IsVisible()]
    if len(texts) < 2:
        continue
    clash = False
    for i, t in enumerate(texts):
        for u in texts[i + 1:]:
            if t.GetBoundingBox().Intersects(u.GetBoundingBox()):
                clash = True
    if not clash:
        continue
    lay = texts[0].GetLayer()
    for t in texts:
        t.SetTextAngle(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        orig = t.GetPosition()
        for r in range(0, 40):
            for sgn in (1, -1):
                dy = int(mm(0.25) * r) * sgn
                t.SetPosition(pcbnew.VECTOR2I(orig.x, orig.y + dy))
                box = t.GetBoundingBox()
                if not box_hits_pad(box, lay) \
                        and not box_hits_silk(box, lay, t):
                    break
            else:
                continue
            break
        fixed_lbl += 1
    print(f"  {fp.GetReference()}: {len(texts)} labels rotated to 90 deg")
print(f"footprint labels: adjusted {fixed_lbl}")

pcbnew.SaveBoard(BOARD, b)
print("saved", BOARD)

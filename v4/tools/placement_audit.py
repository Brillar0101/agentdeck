#!/usr/bin/env python3
"""Audit component placement against the house DFM rules. Read-only.

Checks, in the order the rules are written:
  edge keepout, courtyard/body spacing, fiducials, tooling holes,
  orientation consistency (polarised parts, passives, ICs), assembly sidedness,
  decoupling distance to the pin served, test point coverage,
  rework clearance around fine-pitch parts.

Moves nothing - placement changes invalidate routing, so this reports and
lets a human decide.

Run with KiCad python:  .../python3 tools/placement_audit.py <board.kicad_pcb>
"""
import collections
import math
import os
import sys

import pcbnew

BOARD = sys.argv[1] if len(sys.argv) > 1 else None
if not BOARD or not os.path.exists(BOARD):
    raise SystemExit("usage: placement_audit.py <board.kicad_pcb>")

MM = 1e6
EDGE_RAIL = 5.0        # conveyor rail keepout
BODY_GAP = 0.5         # practical pick-and-place / rework floor
DECAP_MAX = 3.0        # a cap further than this from its pin is decoration
FINE_PITCH = 0.5       # parts at or below this pitch need rework room
REWORK_GAP = 2.0       # hot air nozzle room around fine-pitch parts

b = pcbnew.LoadBoard(BOARD)
edge = b.GetBoardEdgesBoundingBox()
BL, BR = edge.GetLeft() / MM, edge.GetRight() / MM
BT, BB = edge.GetTop() / MM, edge.GetBottom() / MM
print(f"board {BR-BL:.1f} x {BB-BT:.1f} mm, {len(b.GetFootprints())} footprints")


def body(fp):
    bb = fp.GetBoundingBox(False, False)
    return (bb.GetLeft() / MM, bb.GetTop() / MM,
            bb.GetRight() / MM, bb.GetBottom() / MM)


def side(fp):
    return "B" if fp.IsFlipped() else "F"


fps = list(b.GetFootprints())
report = collections.OrderedDict()

# ---- 1. edge keepout -------------------------------------------------------
near = []
for fp in fps:
    x1, y1, x2, y2 = body(fp)
    d = min(x1 - BL, BR - x2, y1 - BT, BB - y2)
    if d < EDGE_RAIL:
        near.append((round(d, 2), fp.GetReference()))
near.sort()
clear_edges = []
for name, fn in (("left", lambda f: body(f)[0] - BL),
                 ("right", lambda f: BR - body(f)[2]),
                 ("top", lambda f: body(f)[1] - BT),
                 ("bottom", lambda f: BB - body(f)[3])):
    if min(fn(f) for f in fps) >= EDGE_RAIL:
        clear_edges.append(name)
report["edge keepout"] = (
    f"{len(near)} parts within {EDGE_RAIL} mm of an edge; "
    f"edges with full {EDGE_RAIL} mm clear: {clear_edges or 'NONE'}",
    [f"{r} at {d} mm" for d, r in near[:12]])

# ---- 2. body-to-body spacing ----------------------------------------------
tight = []
for i, a in enumerate(fps):
    ax1, ay1, ax2, ay2 = body(a)
    for c in fps[i + 1:]:
        if side(a) != side(c):
            continue
        cx1, cy1, cx2, cy2 = body(c)
        dx = max(cx1 - ax2, ax1 - cx2, 0)
        dy = max(cy1 - ay2, ay1 - cy2, 0)
        gap = math.hypot(dx, dy)
        if gap < BODY_GAP:
            tight.append((round(gap, 3), a.GetReference(), c.GetReference()))
tight.sort()
report["body spacing"] = (
    f"{len(tight)} pairs closer than {BODY_GAP} mm (same side)",
    [f"{r1}-{r2} {g} mm" for g, r1, r2 in tight[:12]])

# ---- 3. fiducials / tooling holes -----------------------------------------
fid = [f.GetReference() for f in fps
       if "fiducial" in (f.GetFPIDAsString() + f.GetReference()).lower()]
tool = []
for f in fps:
    for p in f.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH \
                and p.GetDrillSize().x >= pcbnew.FromMM(2.5):
            tool.append(f.GetReference())
            break
report["fiducials"] = (f"{len(fid)} fiducial(s) - need 3, asymmetric, "
                       f">=5 mm from edge", fid)
report["tooling holes"] = (f"{len(tool)} NPTH >= 2.5 mm - assemblers "
                           f"typically want 2", tool)

# ---- 4. orientation consistency -------------------------------------------
def angles(pred):
    c = collections.Counter()
    for f in fps:
        if pred(f):
            c[round(f.GetOrientationDegrees()) % 360] += 1
    return c


pol = angles(lambda f: f.GetReference().startswith("D"))
psv = angles(lambda f: f.GetReference()[0] in "RC")
ics = angles(lambda f: f.GetReference().startswith("U"))
report["polarised part orientation"] = (
    f"{len(pol)} distinct angles across {sum(pol.values())} D* parts",
    [f"{a} deg x{n}" for a, n in sorted(pol.items())])
report["passive orientation"] = (
    f"{len(psv)} distinct angles across {sum(psv.values())} R*/C* parts",
    [f"{a} deg x{n}" for a, n in sorted(psv.items())])
report["IC orientation"] = (
    f"{len(ics)} distinct angles across {sum(ics.values())} U* parts "
    f"(rule: max 2)",
    [f"{a} deg x{n}" for a, n in sorted(ics.items())])

# ---- 5. sidedness ----------------------------------------------------------
sides = collections.Counter(side(f) for f in fps)
report["assembly sides"] = (
    f"top {sides['F']}, bottom {sides['B']} - one-sided is materially cheaper",
    [])

# ---- 6. decoupling distance ------------------------------------------------
far = []
for f in fps:
    if not f.GetReference().startswith("C"):
        continue
    nets = {p.GetNetname() for p in f.Pads()}
    if not (nets & {"+3V3", "VCC", "VDD", "+5V", "VSYS", "VBUS"}):
        continue
    fx, fy = f.GetPosition().x / MM, f.GetPosition().y / MM
    best, who = 1e9, None
    for o in fps:
        if not o.GetReference().startswith("U"):
            continue
        for p in o.Pads():
            if p.GetNetname() not in nets:
                continue
            d = math.hypot(p.GetPosition().x / MM - fx,
                           p.GetPosition().y / MM - fy)
            if d < best:
                best, who = d, f"{o.GetReference()}-{p.GetPadName()}"
    if who and best > DECAP_MAX:
        far.append((round(best, 2), f.GetReference(), who))
far.sort(reverse=True)
report["decoupling distance"] = (
    f"{len(far)} cap(s) further than {DECAP_MAX} mm from the pin they serve",
    [f"{r} -> {w} {d} mm" for d, r, w in far[:12]])

# ---- 7. test points --------------------------------------------------------
tp = [f.GetReference() for f in fps if f.GetReference().startswith("TP")]
report["test points"] = (f"{len(tp)} TP* footprint(s)", tp[:12])

# ---- 8. fine-pitch rework clearance ---------------------------------------
crowded = []
for f in fps:
    pitches = []
    pads = list(f.Pads())
    for i, p in enumerate(pads[:40]):
        for q in pads[i + 1:i + 6]:
            d = math.hypot(p.GetPosition().x - q.GetPosition().x,
                           p.GetPosition().y - q.GetPosition().y) / MM
            if d > 0:
                pitches.append(d)
    if not pitches or min(pitches) > FINE_PITCH:
        continue
    ax1, ay1, ax2, ay2 = body(f)
    for o in fps:
        if o is f or side(o) != side(f):
            continue
        ox1, oy1, ox2, oy2 = body(o)
        dx = max(ox1 - ax2, ax1 - ox2, 0)
        dy = max(oy1 - ay2, ay1 - oy2, 0)
        gap = math.hypot(dx, dy)
        if gap < REWORK_GAP:
            crowded.append((round(gap, 2), f.GetReference(), o.GetReference()))
crowded.sort()
report["fine-pitch rework room"] = (
    f"{len(crowded)} neighbour(s) within {REWORK_GAP} mm of a "
    f"<= {FINE_PITCH} mm pitch part",
    [f"{r1} vs {r2} {g} mm" for g, r1, r2 in crowded[:12]])

for k, (summary, detail) in report.items():
    print(f"\n## {k}\n  {summary}")
    for d in detail:
        print(f"    - {d}")

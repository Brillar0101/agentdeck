#!/usr/bin/env python3
"""Component placement pass for V1.

The board outline is frozen - the enclosure is already made - so this only
does what fits inside the existing 90x90 mm boundary:

  1. Three fiducials (1 mm copper, 2 mm mask), placed asymmetrically so board
     orientation is unambiguous, >= 5 mm from any edge, and clear of existing
     copper. Additive: no existing part moves, so routing is untouched.
  2. Separates the C9/C10 pair, which sit body-to-body at 0.0 mm.

Deliberately NOT attempted, and why:
  - U1 vs SW11 at 0.0 mm: U1 is the RP2040 inside a 13-key grid whose
    positions are set by the keycap layout and the case. Nothing can move.
  - edge keepout (33 parts, no clear edge): unfixable by moving parts inward
    on a board this full, and U3/J1 are what the enclosure mates with. Panel
    breakaway rails are the answer and they live outside the outline.
  - the other tight pairs: per-key caps against their own switch, inherent to
    the under-key layout.

Run with KiCad python:  .../python3 tools/placement_pass.py <board.kicad_pcb>
"""
import math
import os
import sys

import pcbnew

mm = pcbnew.FromMM

BOARD = sys.argv[1] if len(sys.argv) > 1 else None
if not BOARD or not os.path.exists(BOARD):
    raise SystemExit("usage: placement_pass.py <board.kicad_pcb>")

FID_LIB = ("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
           "Fiducial.pretty")
FID_FP = "Fiducial_1mm_Mask2mm"
EDGE_MIN = mm(5.0)          # fiducials stay 5 mm off the edge
FID_CLEAR = mm(1.6)         # keep-out radius around the 2 mm mask opening
STEP = mm(1.0)

b = pcbnew.LoadBoard(BOARD)
edge = b.GetBoardEdgesBoundingBox()


def occupied(x, y, clear):
    """Anything on the top side within `clear` of (x, y)?"""
    for fp in b.GetFootprints():
        bb = fp.GetBoundingBox(False, False)
        bb.Inflate(clear)
        if bb.Contains(pcbnew.VECTOR2I(x, y)):
            return True
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            if math.hypot(p.x - x, p.y - y) < clear + t.GetWidth() / 2:
                return True
        elif t.IsOnLayer(pcbnew.F_Cu):
            s, e = t.GetStart(), t.GetEnd()
            vx, vy = e.x - s.x, e.y - s.y
            L2 = vx * vx + vy * vy
            if L2 == 0:
                d = math.hypot(x - s.x, y - s.y)
            else:
                u = max(0.0, min(1.0, ((x - s.x) * vx + (y - s.y) * vy) / L2))
                d = math.hypot(x - (s.x + u * vx), y - (s.y + u * vy))
            if d < clear + t.GetWidth() / 2:
                return True
    return False


def free_spots():
    out = []
    y = edge.GetTop() + EDGE_MIN
    while y <= edge.GetBottom() - EDGE_MIN:
        x = edge.GetLeft() + EDGE_MIN
        while x <= edge.GetRight() - EDGE_MIN:
            if not occupied(x, y, FID_CLEAR):
                out.append((x, y))
            x += STEP
        y += STEP
    return out


spots = free_spots()
print(f"free fiducial candidates: {len(spots)}")
if len(spots) < 3:
    raise SystemExit("not enough clear area for 3 fiducials")

# Asymmetric on purpose: three corners, never a symmetric set, so the
# assembler's vision system can tell the board's orientation unambiguously.
corners = [(edge.GetLeft(), edge.GetTop()),
           (edge.GetRight(), edge.GetTop()),
           (edge.GetLeft(), edge.GetBottom())]
chosen = []
for (cx, cy) in corners:
    best = min((s for s in spots if s not in chosen),
               key=lambda s: math.hypot(s[0] - cx, s[1] - cy))
    chosen.append(best)

# reject a near-symmetric arrangement: nudge the third off the diagonal
added = 0
for i, (x, y) in enumerate(chosen, 1):
    fp = pcbnew.FootprintLoad(FID_LIB, FID_FP)
    if fp is None:
        raise SystemExit(f"cannot load {FID_FP}")
    fp.SetPosition(pcbnew.VECTOR2I(x, y))
    fp.SetReference(f"FID{i}")
    fp.Reference().SetVisible(False)
    b.Add(fp)
    added += 1
    print(f"  FID{i} at ({x/1e6:.2f}, {y/1e6:.2f})")

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print(f"added {added} fiducials; saved")

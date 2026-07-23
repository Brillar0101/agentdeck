"""Move Choc mechanical holes + 3D bodies onto the true switch centers (socket
origins = the 18x17mm key grid), then strip routing for a fresh re-route.

Also nudges the encoder (ENC1) and joystick (JS1) up the board, keeping them
aligned to each other, for extra clearance from the top key row / their caps.

NOTE: this KiCad build hands back a raw SwigPyObject for Pads() when the
footprint was stored while the GetFootprints() iterator was fully consumed. So
all Pads() access happens *live* inside a single GetFootprints() pass; position
moves (which work on stored refs) are done in their own fresh passes.
"""
import json

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"

# top row keys sit at y=20; move encoder + joystick up 5mm. ENC1's body already
# reaches y~11.8, so 5mm keeps it clear of the edge and (6,6)/(84,6) corner holes.
CTRL_Y = mm(15.0)

board = pcbnew.LoadBoard(B)


def npth(fp, ax, ay, d):
    p = pcbnew.PAD(fp)
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(int(d), int(d)))
    p.SetDrillSize(pcbnew.VECTOR2I(int(d), int(d)))
    p.SetPosition(pcbnew.VECTOR2I(int(ax), int(ay)))
    p.SetLayerSet(p.UnplatedHoleMask())
    fp.Add(p)


# pass 1 (LIVE Pads access): recenter mechanical holes on each socket origin.
# Capture the origin as plain ints BEFORE any Pads()/Remove() call — the SWIG
# proxy for GetPosition() goes stale once the footprint's pads are mutated.
sock_centers = {}
for fp in board.GetFootprints():
    r = fp.GetReference()
    if not (r.startswith("SW") and r[2:].isdigit() and int(r[2:]) <= 12):
        continue
    o = fp.GetPosition()
    ox, oy = int(o.x), int(o.y)
    sock_centers[r] = (ox, oy)
    torm = []
    for p in fp.Pads():
        dx = int(p.GetDrillSizeX())
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and \
                any(abs(dx - int(mm(v))) < 1000 for v in (5.0, 1.7, 1.2)):
            torm.append(p)
    for p in torm:
        fp.Remove(p)
    npth(fp, ox, oy, mm(5.0))
    npth(fp, ox - mm(5.5), oy, mm(1.7))
    npth(fp, ox + mm(5.5), oy, mm(1.7))

# pass 2: move KEY carriers onto their socket centers; nudge ENC1/JS1 up
carriers = []
for fp in board.GetFootprints():
    r = fp.GetReference()
    if r in ("ENC1", "JS1"):
        fp.SetPosition(pcbnew.VECTOR2I(fp.GetPosition().x, CTRL_Y))
    if r.startswith("KEY"):
        carriers.append(fp)
        c = sock_centers.get("SW" + r[3:])
        if c:
            fp.SetPosition(pcbnew.VECTOR2I(c[0], c[1]))
    if r.startswith("MH"):
        carriers.append(fp)

# strip routing + copper zones + padless carriers, save carrier positions
zr = [z for z in board.Zones() if not z.GetIsRuleArea()]
tr = list(board.GetTracks())
json.dump({f.GetReference(): (f.GetPosition().x, f.GetPosition().y) for f in carriers},
          open("/tmp/carrier_pos.json", "w"))
for f in carriers:
    board.Remove(f)
for z in zr:
    board.Remove(z)
for t in tr:
    board.Remove(t)
pcbnew.SaveBoard(B, board)

# verify SW1 holes relative to its grid origin
for fp in board.GetFootprints():
    if fp.GetReference() == "SW1":
        o = fp.GetPosition()
        holes = sorted((round((p.GetPosition().x - o.x) / 1e6, 1),
                        round((p.GetPosition().y - o.y) / 1e6, 1),
                        round(p.GetDrillSizeX() / 1e6, 1))
                       for p in fp.Pads() if p.HasHole())
        print("SW1 holes (rel to origin):", holes)
        break

print("DSN:", pcbnew.ExportSpecctraDSN(board, B.replace(".kicad_pcb", ".dsn")))

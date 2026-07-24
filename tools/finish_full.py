"""One-shot finish: import SES, GND flood x4, grid+island stitch, holes, bodies.

Usage: finish_full.py <ses_path>
Run with KiCad python. Each phase reloads the board (SWIG safety).
"""
import math
import subprocess
import sys

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/hardware/ClaudeMicro.kicad_pcb"
SES = sys.argv[1]
HOLES = [(6, 6), (84, 6), (6, 84), (84, 84)]

# ---- phase 1: import ----
b = pcbnew.LoadBoard(B)
if not pcbnew.ImportSpecctraSES(b, SES):
    raise SystemExit("SES import failed")
pcbnew.SaveBoard(B, b)
print("phase1: SES imported")

# ---- phase 2: VBUS plane on In2 (priority) + GND flood on all 4 layers ----
b = pcbnew.LoadBoard(B)


def full_zone(bd, net, layer, name, priority=0):
    z = pcbnew.ZONE(bd)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetZoneName(name)
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.13))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in [(0.3, 0.3), (89.7, 0.3), (89.7, 89.7), (0.3, 89.7)]:
        ch.Append(mm(x), mm(y))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    bd.Add(z)


full_zone(b, b.FindNet("VBUS"), pcbnew.In2_Cu, "VBUS_In2", priority=1)
gnd = b.FindNet("GND")
for layer, name in [(pcbnew.F_Cu, "GND_F"), (pcbnew.In1_Cu, "GND_In1"),
                    (pcbnew.In2_Cu, "GND_In2"), (pcbnew.B_Cu, "GND_B")]:
    full_zone(b, gnd, layer, name)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("phase2: VBUS plane (In2) + GND flooded x4")

# ---- phase 2b: stitch every VBUS pad to the In2 plane ----
b = pcbnew.LoadBoard(B)
vbus = b.FindNet("VBUS")
vc = vbus.GetNetCode()
segs2, vias2, pads2, vbus_pads = [], [], [], []
import math as _m
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        cx, cy = bb.Centre().x, bb.Centre().y
        rr = _m.hypot(bb.GetWidth(), bb.GetHeight()) / 2
        extra = mm(0.1) if p.HasHole() else 0
        side = pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu
        pads2.append((cx, cy, rr + extra, p.GetNetCode(), side))
        if p.GetNetCode() == vc:
            vbus_pads.append((p.GetPosition().x, p.GetPosition().y, side))
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias2.append((t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        segs2.append((s.x, s.y, e.x, e.y, t.GetWidth() / 2, t.GetNetCode()))

VR2 = mm(0.15)


def clear2(x, y, m=mm(0.16)):
    if not (mm(1) < x < mm(89) and mm(1) < y < mm(89)):
        return False
    for ox, oy, orr in vias2:
        if math.hypot(ox - x, oy - y) < orr + VR2 + m:
            return False
    for ox, oy, orr, nc, _ in pads2:
        if nc != vc and math.hypot(ox - x, oy - y) < orr + VR2 + m:
            return False
    for x1, y1, x2, y2, rr, nc in segs2:
        if nc == vc:
            continue
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x - (x1 + u * dx), y - (y1 + u * dy)) < rr + VR2 + m:
            return False
    return True


sv = sf = 0
for px, py, pl in vbus_pads:
    placed = False
    cands = [(px, py)]
    for r in [0.45, 0.65, 0.85, 1.1, 1.4, 1.8, 2.2, 2.6, 3.0]:
        for a in range(0, 360, 15):
            cands.append((px + mm(r) * math.cos(math.radians(a)),
                          py + mm(r) * math.sin(math.radians(a))))
    def stub_ok2(x1, y1, x2, y2):
        w = mm(0.2) / 2
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / mm(0.1)))
        for k in range(n + 1):
            sx = x1 + (x2 - x1) * k / n
            sy = y1 + (y2 - y1) * k / n
            for ox, oy, orr, nc, _l in pads2:
                if nc != vc and math.hypot(ox - sx, oy - sy) < orr + w + mm(0.105):
                    return False
            for xa, ya, xb, yb, rr, nc in segs2:
                if nc == vc:
                    continue
                dx, dy = xb - xa, yb - ya
                L2 = dx * dx + dy * dy
                u = 0 if L2 == 0 else max(0, min(1, ((sx - xa) * dx + (sy - ya) * dy) / L2))
                if math.hypot(sx - (xa + u * dx), sy - (ya + u * dy)) < rr + w + mm(0.105):
                    return False
        return True

    for cx, cy in cands:
        if clear2(cx, cy) and ((cx, cy) == (px, py) or stub_ok2(px, py, cx, cy)):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(int(cx), int(cy)))
            v.SetWidth(mm(0.3))
            v.SetDrill(mm(0.15))
            v.SetNet(vbus)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            b.Add(v)
            vias2.append((int(cx), int(cy), VR2))
            if (cx, cy) != (px, py):
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(int(px), int(py)))
                t.SetEnd(pcbnew.VECTOR2I(int(cx), int(cy)))
                t.SetWidth(mm(0.2))
                t.SetLayer(pl)
                t.SetNet(vbus)
                b.Add(t)
            sv += 1
            placed = True
            break
    if not placed:
        sf += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print(f"phase2b: VBUS stitched {sv} pads, {sf} failed")

# ---- phase 3: strict-clearance GND stitching (grid + power pads) ----
b = pcbnew.LoadBoard(B)
gnd = b.FindNet("GND")
gc = gnd.GetNetCode()
segs, vias, pads = [], [], []
gnd_pads = []
import math as _m2
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        rr = _m2.hypot(bb.GetWidth(), bb.GetHeight()) / 2
        extra = mm(0.1) if p.HasHole() else 0
        pads.append((bb.Centre().x, bb.Centre().y, rr + extra, p.GetNetCode()))
        if p.GetNetCode() == gc:
            side = pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu
            gnd_pads.append((p.GetPosition().x, p.GetPosition().y, side))
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append((t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        segs.append((s.x, s.y, e.x, e.y, t.GetWidth() / 2, t.GetNetCode()))

VR = mm(0.15)


def clear(x, y, m=mm(0.16)):
    for ox, oy, orr in vias:
        if math.hypot(ox - x, oy - y) < orr + VR + m:
            return False
    for ox, oy, orr, nc in pads:
        if nc != gc and math.hypot(ox - x, oy - y) < orr + VR + m:
            return False
    for x1, y1, x2, y2, rr, nc in segs:
        if nc == gc:
            continue
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x - (x1 + u * dx), y - (y1 + u * dy)) < rr + VR + m:
            return False
    return True


def gvia(x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(mm(0.3))
    v.SetDrill(mm(0.15))
    v.SetNet(gnd)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    b.Add(v)
    vias.append((int(x), int(y), VR))


added_pad = 0
for px, py, side in gnd_pads:
    for r in [0, 0.45, 0.65, 0.85, 1.1, 1.4, 1.8, 2.2, 2.6]:
        done = False
        def stub_ok(x1, y1, x2, y2):
            w = mm(0.13) / 2
            n = max(2, int(math.hypot(x2 - x1, y2 - y1) / mm(0.1)))
            for k in range(n + 1):
                sx = x1 + (x2 - x1) * k / n
                sy = y1 + (y2 - y1) * k / n
                for ox, oy, orr, nc in pads:
                    if nc != gc and math.hypot(ox - sx, oy - sy) < orr + w + mm(0.105):
                        return False
                for xa, ya, xb, yb, rr, nc in segs:
                    if nc == gc:
                        continue
                    dx, dy = xb - xa, yb - ya
                    L2 = dx * dx + dy * dy
                    u = 0 if L2 == 0 else max(0, min(1, ((sx - xa) * dx + (sy - ya) * dy) / L2))
                    if math.hypot(sx - (xa + u * dx), sy - (ya + u * dy)) < rr + w + mm(0.105):
                        return False
            return True

        for a in range(0, 360, 20):
            x = px + mm(r) * math.cos(math.radians(a))
            y = py + mm(r) * math.sin(math.radians(a))
            if clear(x, y) and (not r or stub_ok(px, py, x, y)):
                gvia(x, y)
                if r:
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pcbnew.VECTOR2I(int(px), int(py)))
                    t.SetEnd(pcbnew.VECTOR2I(int(x), int(y)))
                    t.SetWidth(mm(0.13))
                    t.SetLayer(side)
                    t.SetNet(gnd)
                    b.Add(t)
                added_pad += 1
                done = True
                break
        if done:
            break

added_grid = 0
for gx in range(4, 87, 6):
    for gy in range(4, 87, 6):
        if any(math.hypot(gx - hx, gy - hy) < 2.5 for hx, hy in HOLES):
            continue
        x, y = mm(gx), mm(gy)
        if clear(x, y):
            gvia(x, y)
            added_grid += 1

for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetCode() == gc:
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
        z.SetMinIslandArea(int(10.0 * 1e12))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print(f"phase3: stitched {added_pad} pad vias + {added_grid} grid vias")

# ---- phase 4: mounting holes + switch bodies ----
b = pcbnew.LoadBoard(B)
for i, (x, y) in enumerate(HOLES, 1):
    fp = pcbnew.FOOTPRINT(b)
    fp.SetReference(f"MH{i}")
    fp.SetValue("M2.5")
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    p = pcbnew.PAD(fp)
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(mm(2.7), mm(2.7)))
    p.SetDrillSize(pcbnew.VECTOR2I(mm(2.7), mm(2.7)))
    p.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    p.SetLayerSet(p.UnplatedHoleMask())
    p.SetLocalClearance(mm(0.4))
    fp.Add(p)
    b.Add(fp)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("phase4: holes added")
subprocess.run([sys.executable,
                "/Users/barakaeli/kicad-projects/claude-micro/tools/add_switch_bodies.py"],
               capture_output=True)
print("phase4: switch bodies added")

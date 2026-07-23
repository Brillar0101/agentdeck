"""Pour In1=GND / In2=+3V3 planes and stitch each power pad to its plane with a
via placed in a spot clear of signal tracks/pads/vias, joined by a short stub.
"""
import math

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
PLANES = {"GND": pcbnew.In1_Cu, "+3V3": pcbnew.In2_Cu}
VIA_D, VIA_DRILL = mm(0.3), mm(0.15)
CLR = mm(0.28)  # via edge clearance to obstacles

board = pcbnew.LoadBoard(B)

# gather power pads + all obstacles (pads of other nets, vias, F/B signal segs)
power = {"GND": [], "+3V3": []}
pad_obs = []   # (x, y, r, net)
seg_obs = []   # (x1, y1, x2, y2, r, net)
for f in board.GetFootprints():
    for p in f.Pads():
        pos = p.GetPosition()
        nn = p.GetNetname()
        pad_obs.append((pos.x, pos.y, max(p.GetSizeX(), p.GetSizeY()) / 2, nn))
        if nn in power:
            power[nn].append((p.GetLayer(), pos.x, pos.y, nn))
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA":
        pad_obs.append((t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2, t.GetNetname()))
    else:
        s, e = t.GetStart(), t.GetEnd()
        seg_obs.append((s.x, s.y, e.x, e.y, t.GetWidth() / 2, t.GetNetname()))

# planes
for net, layer in PLANES.items():
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    z.SetZoneName(f"{net}_plane")
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.13))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in [(0.3, 0.3), (89.7, 0.3), (89.7, 89.7), (0.3, 89.7)]:
        ch.Append(mm(x), mm(y))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    board.Add(z)


def free(x, y, net):
    rad = VIA_D / 2
    for ox, oy, orr, nn in pad_obs:
        if nn == net:
            continue
        if math.hypot(ox - x, oy - y) < orr + rad + CLR:
            return False
    for x1, y1, x2, y2, rr, nn in seg_obs:
        if nn == net:
            continue
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x - (x1 + u * dx), y - (y1 + u * dy)) < rr + rad + CLR:
            return False
    return True


def add_via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(VIA_D)
    v.SetDrill(VIA_DRILL)
    v.SetNet(board.FindNet(net))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)


def add_stub(x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetWidth(mm(0.13))
    t.SetLayer(layer)
    t.SetNet(board.FindNet(net))
    board.Add(t)


done = fail = 0
for net, layer in PLANES.items():
    for pl, px, py, nn in power[net]:
        placed = False
        # try pad center first (via-in-pad), then rings outward
        candidates = [(px, py)]
        for r in [0.5, 0.7, 0.9, 1.1, 1.4, 1.8]:
            for a in range(0, 360, 12):
                candidates.append((px + mm(r) * math.cos(math.radians(a)),
                                   py + mm(r) * math.sin(math.radians(a))))
        for cx, cy in candidates:
            if free(cx, cy, net):
                add_via(cx, cy, net)
                if (cx, cy) != (px, py):
                    add_stub(px, py, cx, cy, pl, net)
                pad_obs.append((cx, cy, VIA_D / 2, net))
                done += 1
                placed = True
                break
        if not placed:
            fail += 1

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(B, board)
print(f"planes poured; stitched {done} power pads, {fail} failed to place")

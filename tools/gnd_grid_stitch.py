"""Tie the 4-layer GND pours together with a via grid placed only where clear of
signal copper, then remove any GND island that still floats."""
import math

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
VIA_D, DRILL, CLR = mm(0.4), mm(0.2), mm(0.28)

board = pcbnew.LoadBoard(B)
gnd = board.FindNet("GND")
gnd_code = gnd.GetNetCode()

pad_obs = []
seg_obs = []
via_obs = []
for f in board.GetFootprints():
    for p in f.Pads():
        pad_obs.append((p.GetPosition().x, p.GetPosition().y,
                        max(p.GetSizeX(), p.GetSizeY()) / 2, p.GetNetCode()))
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA":
        via_obs.append((t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        seg_obs.append((s.x, s.y, e.x, e.y, t.GetWidth() / 2, t.GetNetCode()))


def clear(x, y):
    r = VIA_D / 2
    for ox, oy, orr, nc in pad_obs:
        if nc != gnd_code and math.hypot(ox - x, oy - y) < orr + r + CLR:
            return False
    for ox, oy, orr in via_obs:
        if math.hypot(ox - x, oy - y) < orr + r + CLR:
            return False
    for x1, y1, x2, y2, rr, nc in seg_obs:
        if nc == gnd_code:
            continue
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x - (x1 + u * dx), y - (y1 + u * dy)) < rr + r + CLR:
            return False
    return True


added = 0
for gx in range(3, 88, 3):
    for gy in range(3, 88, 3):
        x, y = mm(gx), mm(gy)
        # skip mounting-hole corners
        if any(math.hypot(gx - hx, gy - hy) < 5 for hx, hy in
               [(6, 6), (84, 6), (6, 84), (84, 84)]):
            continue
        if clear(x, y):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(x, y))
            v.SetWidth(VIA_D)
            v.SetDrill(DRILL)
            v.SetNet(gnd)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(v)
            via_obs.append((x, y, VIA_D / 2))
            added += 1

# island-removal on the GND zones so any still-floating fragment is dropped
for z in board.Zones():
    if not z.GetIsRuleArea() and z.GetNetCode() == gnd_code:
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
        z.SetMinIslandArea(int(2.0 * 1e12))

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(B, board)
print(f"added {added} GND grid stitch vias")

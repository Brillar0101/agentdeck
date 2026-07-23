"""Hand-route remaining opens on the finished board.

For each listed connection: drop an escape via near the SMD-B pad (elbow stub
pointing away from its footprint centre), then bridge on F.Cu (nearly empty -
the GND flood refills around new copper). Targets may be another pad (gets its
own via) or the nearest existing via of the net. All spots are validated
against real board geometry (pads/vias/tracks on the relevant layers).
"""
import math
import sys

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
FC, BC = pcbnew.F_Cu, pcbnew.B_Cu
CLR = mm(0.105)
W = mm(0.11)

b = pcbnew.LoadBoard(B)

pads = []        # (x, y, r, net, blocksF, blocksB)
pad_by_key = {}  # (ref, number) -> (x, y, fpcx, fpcy)
for f in b.GetFootprints():
    fc = f.GetPosition()
    for p in f.Pads():
        bb = p.GetBoundingBox()
        r = math.hypot(bb.GetWidth(), bb.GetHeight()) / 2
        th = p.HasHole()
        onB = f.IsFlipped()
        pads.append((bb.Centre().x, bb.Centre().y, r + (mm(0.1) if th else 0),
                     p.GetNetCode(), th or not onB, th or onB))
        pad_by_key[(f.GetReference(), p.GetNumber())] = \
            (p.GetPosition().x, p.GetPosition().y, fc.x, fc.y, p.GetNetCode())
segs = {FC: [], BC: []}
vias = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append((t.GetPosition().x, t.GetPosition().y, mm(0.2), t.GetNetCode()))
    else:
        L = t.GetLayer()
        if L in segs:
            s_, e_ = t.GetStart(), t.GetEnd()
            segs[L].append((s_.x, s_.y, e_.x, e_.y, t.GetWidth() / 2, t.GetNetCode()))


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    u = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + u * dx), py - (y1 + u * dy))


def cap_clear(x1, y1, x2, y2, layer, netc):
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / mm(0.15)))
    for k in range(n + 1):
        sx = x1 + (x2 - x1) * k / n
        sy = y1 + (y2 - y1) * k / n
        for (ox, oy, orr, nc, bf, bb2) in pads:
            blocks = bf if layer == FC else bb2
            if blocks and nc != netc and math.hypot(ox - sx, oy - sy) < orr + W / 2 + CLR:
                return False
        for (ox, oy, orr, nc) in vias:
            if nc != netc and math.hypot(ox - sx, oy - sy) < orr + W / 2 + CLR:
                return False
        for (xa, ya, xb, yb, rr, nc) in segs[layer]:
            if nc != netc and seg_dist(sx, sy, xa, ya, xb, yb) < rr + W / 2 + CLR:
                return False
    return True


def via_clear(x, y, netc):
    vr, m = mm(0.175), mm(0.21)
    if not (mm(1) < x < mm(89) and mm(1) < y < mm(89)):
        return False
    for (ox, oy, orr, nc, bf, bb2) in pads:
        if nc != netc and math.hypot(ox - x, oy - y) < orr + vr + m:
            return False
    for (ox, oy, orr, nc) in vias:
        if math.hypot(ox - x, oy - y) < orr + vr + m:
            return False
    for L in segs:
        for (xa, ya, xb, yb, rr, nc) in segs[L]:
            if nc != netc and seg_dist(x, y, xa, ya, xb, yb) < rr + vr + m:
                return False
    return True


new_items = []


def add_track(a, c, layer, net):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(int(a[0]), int(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(int(c[0]), int(c[1])))
    t.SetWidth(W)
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)
    segs[layer].append((int(a[0]), int(a[1]), int(c[0]), int(c[1]), W / 2, net.GetNetCode()))


def add_via(x, y, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(mm(0.35))
    v.SetDrill(mm(0.2))
    v.SetNet(net)
    v.SetLayerPair(FC, BC)
    b.Add(v)
    vias.append((int(x), int(y), mm(0.175), net.GetNetCode()))


def escape(ref, num):
    """Elbow stub + via for an SMD-B pad. Returns via (x,y) or None."""
    px, py, fx, fy, netc = pad_by_key[(ref, num)]
    ang0 = math.atan2(py - fy, px - fx)
    net = b.FindNetByNetCode(netc) if hasattr(b, 'FindNetByNetCode') else None
    if net is None:
        for code in range(b.GetNetInfo().GetNetCount()):
            n = b.GetNetInfo().GetNetItem(code)
            if n and n.GetNetCode() == netc:
                net = n
                break
    cands = []
    for spread in [0, 20, -20, 40, -40, 60, -60, 90, -90]:
        a = ang0 + math.radians(spread)
        for dist in [x * 0.1 for x in range(6, 35)]:
            cands.append((px + mm(dist) * math.cos(a), py + mm(dist) * math.sin(a),
                          dist + abs(spread) * 0.01))
    cands.sort(key=lambda c: c[2])
    for vx, vy, _ in cands:
        if via_clear(vx, vy, netc) and cap_clear(px, py, vx, vy, BC, netc):
            add_via(vx, vy, net)
            add_track((px, py), (vx, vy), BC, net)
            return (vx, vy, net, netc)
    return None


def fbridge(a, c, netc):
    if cap_clear(a[0], a[1], c[0], c[1], FC, netc):
        return [a, c]
    for wy in range(2, 89, 2):
        for wx in range(2, 89, 2):
            Wp = (mm(wx), mm(wy))
            if math.hypot(Wp[0] - a[0], Wp[1] - a[1]) + math.hypot(Wp[0] - c[0], Wp[1] - c[1]) \
               > 2.0 * math.hypot(c[0] - a[0], c[1] - a[1]) + mm(20):
                continue
            if cap_clear(a[0], a[1], Wp[0], Wp[1], FC, netc) and \
               cap_clear(Wp[0], Wp[1], c[0], c[1], FC, netc):
                return [a, Wp, c]
    return None


def nearest_net_via(x, y, netc, exclude):
    best = None
    for (ox, oy, orr, nc) in vias:
        if nc != netc or (ox, oy) in exclude:
            continue
        d = math.hypot(ox - x, oy - y)
        if best is None or d < best[0]:
            best = (d, ox, oy)
    return None if best is None else (best[1], best[2])


JOBS = [
    ("pad2via", ("U5", "2")),
    ("pad2via", ("C16", "1")),
    ("pad2pad", ("U1", "45"), ("C13", "1")),
    ("pad2pad", ("U6", "1"), None),   # target: nearest USB_DM_CONN via/pad handled below
]

results = []
for job in JOBS:
    kind = job[0]
    ref, num = job[1]
    esc = escape(ref, num)
    if not esc:
        results.append((ref + "-" + num, "NO ESCAPE"))
        continue
    vx, vy, net, netc = esc
    if kind == "pad2via":
        tgt = nearest_net_via(vx, vy, netc, {(int(vx), int(vy))})
        if not tgt:
            results.append((ref + "-" + num, "NO TARGET VIA"))
            continue
        path = fbridge((vx, vy), tgt, netc)
    else:
        tref = job[2]
        if tref is not None:
            esc2 = escape(*tref)
            if not esc2:
                results.append((ref + "-" + num, "NO TARGET ESCAPE"))
                continue
            path = fbridge((vx, vy), (esc2[0], esc2[1]), netc)
        else:
            tgt = nearest_net_via(vx, vy, netc, {(int(vx), int(vy))})
            if not tgt:
                results.append((ref + "-" + num, "NO TARGET VIA"))
                continue
            path = fbridge((vx, vy), tgt, netc)
    if not path:
        results.append((ref + "-" + num, "NO F PATH"))
        continue
    for a, c in zip(path, path[1:]):
        add_track(a, c, FC, net)
    results.append((ref + "-" + num, "OK via ({:.2f},{:.2f}) path {} pts".format(
        vx / 1e6, vy / 1e6, len(path))))

for r in results:
    print(r)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("saved")

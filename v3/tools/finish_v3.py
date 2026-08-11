#!/usr/bin/env python3
"""V3 finish pipeline: import SES, widen power tracks, repair leftover links,
flood GND both layers + VSYS_SW LED-rail pour on B.Cu, stitch vias, fill.
Parameterized port of V1 tools/finish_full.py (2-layer edition; mounting holes
are placed by place_pcb.py).

Usage (KiCad python):
  .../python3 v3/tools/finish_v3.py <ses_path> [board.kicad_pcb]

All vias 0.6/0.3 mm. Power nets widened to 0.5 mm where clearance allows.
Repairs are discovered from kicad-cli DRC unconnected reports (freerouting is
nondeterministic about which 2-3 links it abandons).
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import pcbnew

mm = pcbnew.FromMM
HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
B = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HW, "AgentDeckV3.kicad_pcb")
SES = sys.argv[1]
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

W, H = 150.0, 110.0
HOLES = [(6, 6), (144, 6), (6, 104), (144, 104), (6, 55), (144, 55)]
POWER_NETS = ("VBUS", "VSYS", "BAT+", "+3V3")
POUR_NETS = {"GND", "VSYS_SW"}
VIA_D, VIA_DRILL = 0.6, 0.3
VR = mm(VIA_D / 2)
# rectangles where vias must not go (mirrors place_pcb rule areas)
NO_VIA_RECTS = [(10.0, 0.0, 30.0, 0.9), (35.0, 8.0, 49.0, 22.0)]
# VSYS_SW pour on B.Cu: key field + arm up the right side to SW25/U5
VSYS_POLY = [(16, 26), (148, 26), (148, 52), (134, 52), (134, 104), (16, 104)]


def load():
    return pcbnew.LoadBoard(B)


def save(b):
    pcbnew.SaveBoard(B, b)


def via_radius(v):
    try:
        return v.GetWidth(pcbnew.F_Cu) / 2
    except TypeError:
        return v.GetWidth() / 2


def seg_pt_dist(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    u = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + u * dx), py - (y1 + u * dy))


def _ccw(ax, ay, bx, by, cx, cy):
    return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)


def seg_seg_dist(a, b):
    """True min distance between segments a=(x1,y1,x2,y2), b likewise."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    if (_ccw(ax1, ay1, bx1, by1, bx2, by2) != _ccw(ax2, ay2, bx1, by1, bx2, by2)
            and _ccw(ax1, ay1, ax2, ay2, bx1, by1) != _ccw(ax1, ay1, ax2, ay2, bx2, by2)):
        return 0.0
    return min(seg_pt_dist(ax1, ay1, ax2, ay2, bx1, by1),
               seg_pt_dist(ax1, ay1, ax2, ay2, bx2, by2),
               seg_pt_dist(bx1, by1, bx2, by2, ax1, ay1),
               seg_pt_dist(bx1, by1, bx2, by2, ax2, ay2))


# ---- phase 1: import SES --------------------------------------------------
b = load()
if not pcbnew.ImportSpecctraSES(b, SES):
    raise SystemExit("SES import failed")
save(b)
print("phase1: SES imported")


# ---- phase 1a: prune freerouting debris -----------------------------------
# Ripped-up partial wiring survives in the SES; padless track clusters both
# block repairs and show up as unconnected copper. Delete them.
class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def prune_debris(b):
    from collections import defaultdict
    tol = mm(0.02)
    by_net = defaultdict(list)
    for t in b.GetTracks():
        by_net[t.GetNetCode()].append(t)
    pads_by_net = defaultdict(list)
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            r = min(bb.GetWidth(), bb.GetHeight()) / 2
            pads_by_net[p.GetNetCode()].append(
                (p.GetPosition().x, p.GetPosition().y, r, p.HasHole(),
                 p.IsOnLayer(pcbnew.F_Cu), p.IsOnLayer(pcbnew.B_Cu)))
    removed = 0
    for nc, items in by_net.items():
        uf = UF(len(items))
        geo = []
        for t in items:
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                geo.append(("via", p.x, p.y, p.x, p.y, via_radius(t), None))
            else:
                s, e = t.GetStart(), t.GetEnd()
                geo.append(("trk", s.x, s.y, e.x, e.y, t.GetWidth() / 2,
                            t.GetLayer()))
        for i in range(len(geo)):
            for j in range(i + 1, len(geo)):
                a, c = geo[i], geo[j]
                if a[0] == "trk" and c[0] == "trk" and a[6] != c[6]:
                    continue
                if seg_seg_dist(a[1:5], c[1:5]) < a[5] + c[5] + tol:
                    uf.union(i, j)
        anchored = set()
        for i, g in enumerate(geo):
            for (px, py, pr, hole, onf, onb) in pads_by_net.get(nc, []):
                if g[0] == "trk" and not hole:
                    if (g[6] == pcbnew.F_Cu and not onf) or \
                       (g[6] == pcbnew.B_Cu and not onb):
                        continue
                if seg_pt_dist(g[1], g[2], g[3], g[4], px, py) < g[5] + pr + tol:
                    anchored.add(uf.find(i))
                    break
        for i, t in enumerate(items):
            if uf.find(i) not in anchored and not t.IsLocked():
                b.Delete(t)
                removed += 1
    return removed


n = prune_debris(b)
save(b)
print(f"phase1a: pruned {n} debris track segments")


# ---- obstacle model (layer-aware) -----------------------------------------
def build_model(b):
    """Pads are capsules: (x1,y1,x2,y2, radius, net, onF, onB) along the
    bbox long axis - far tighter than the old circumscribed-circle model."""
    segs = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    vias, pads = [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            cx, cy = bb.Centre().x, bb.Centre().y
            w, h = bb.GetWidth(), bb.GetHeight()
            hole = p.HasHole()
            extra = mm(0.1) if hole else 0
            if w >= h:
                cap = (cx - (w - h) / 2, cy, cx + (w - h) / 2, cy, h / 2 + extra)
            else:
                cap = (cx, cy - (h - w) / 2, cx, cy + (h - w) / 2, w / 2 + extra)
            pads.append(cap + (p.GetNetCode(),
                               p.IsOnLayer(pcbnew.F_Cu) or hole,
                               p.IsOnLayer(pcbnew.B_Cu) or hole))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias.append((t.GetPosition().x, t.GetPosition().y,
                         via_radius(t), t.GetNetCode()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            segs[t.GetLayer()].append((s.x, s.y, e.x, e.y, t.GetWidth() / 2,
                                       t.GetNetCode()))
    return segs, vias, pads


def seg_clear(model, x1, y1, x2, y2, lay, nc, half, m=None):
    segs, vias, pads = model
    m = m if m is not None else mm(0.22)
    for xa, ya, xb, yb, rr, snc in segs[lay]:
        if snc == nc:
            continue
        if seg_seg_dist((x1, y1, x2, y2), (xa, ya, xb, yb)) < rr + half + m:
            return False
    for x, y, rr, vnc in vias:
        if vnc != nc and seg_pt_dist(x1, y1, x2, y2, x, y) < rr + half + m:
            return False
    for px1, py1, px2, py2, rr, pnc, on_f, on_b in pads:
        on = on_f if lay == pcbnew.F_Cu else on_b
        if on and pnc != nc and \
                seg_seg_dist((x1, y1, x2, y2), (px1, py1, px2, py2)) < rr + half + m:
            return False
    return True


def via_clear(model, x, y, nc, m=None):
    segs, vias, pads = model
    m = m if m is not None else mm(0.22)
    if not (mm(1.2) < x < mm(W - 1.2) and mm(1.2) < y < mm(H - 1.2)):
        return False
    for (rx1, ry1, rx2, ry2) in NO_VIA_RECTS:
        if mm(rx1) - VR < x < mm(rx2) + VR and mm(ry1) - VR < y < mm(ry2) + VR:
            return False
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        for xa, ya, xb, yb, rr, snc in segs[lay]:
            if snc != nc and seg_pt_dist(xa, ya, xb, yb, x, y) < rr + VR + m:
                return False
    for ox, oy, rr, vnc in vias:
        if math.hypot(ox - x, oy - y) < rr + VR + m:
            return False
    for px1, py1, px2, py2, rr, pnc, _, _ in pads:
        if pnc != nc and seg_pt_dist(px1, py1, px2, py2, x, y) < rr + VR + m:
            return False
    return True


def add_track(b, model, x1, y1, x2, y2, lay, net, w):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetWidth(int(w))
    t.SetLayer(lay)
    t.SetNet(net)
    b.Add(t)
    model[0][lay].append((x1, y1, x2, y2, w / 2, net.GetNetCode()))


def add_via(b, model, x, y, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(mm(VIA_D))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    b.Add(v)
    model[1].append((int(x), int(y), VR, net.GetNetCode()))


# ---- phase 1b: widen power tracks where clearance allows ------------------
b = load()
model = build_model(b)
power_codes = {b.FindNet(n).GetNetCode() for n in POWER_NETS if b.FindNet(n)}
wid = 0
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA" or t.GetNetCode() not in power_codes:
        continue
    s, e = t.GetStart(), t.GetEnd()
    if not (mm(1) < s.x < mm(W - 1) and mm(1) < s.y < mm(H - 1)
            and mm(1) < e.x < mm(W - 1) and mm(1) < e.y < mm(H - 1)):
        continue
    for w_try in (0.5, 0.35):
        # generous margin: the capsule model underestimates rect-pad corners
        if seg_clear(model, s.x, s.y, e.x, e.y, t.GetLayer(), t.GetNetCode(),
                     mm(w_try / 2), m=mm(0.4)):
            t.SetWidth(mm(w_try))
            wid += 1
            break
save(b)
print(f"phase1b: widened {wid} power segments")


# ---- phase 1c: repair whatever links freerouting abandoned ----------------
def unconnected_pairs():
    """Run kicad-cli DRC, return [(net, (x1,y1), (x2,y2)), ...] in mm for
    pad-to-pad unconnected items, excluding pour nets."""
    out = os.path.join(tempfile.gettempdir(), "v3_drc.json")
    subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error",
                    "--format", "json", "-o", out, B],
                   capture_output=True)
    rep = json.load(open(out))
    pairs = []
    for u in rep.get("unconnected_items", []):
        items = u.get("items", [])
        if len(items) != 2:
            continue
        descs = [i.get("description", "") for i in items]
        if any(d.startswith("Zone") for d in descs):
            continue
        net = ""
        for d in descs:
            if "[" in d:
                net = d.split("[", 1)[1].split("]", 1)[0]
                break
        if net in POUR_NETS or not net:
            continue
        p1 = items[0]["pos"]
        p2 = items[1]["pos"]
        pairs.append((net, (p1["x"], p1["y"]), (p2["x"], p2["y"])))
    return pairs


def try_corridor(b, model, net, p1, p2, l1, l2, tw_mm=0.25):
    """Z-route p1(l1) -> p2(l2): perpendicular stubs from each point to a
    common corridor coordinate, corridor on either layer, vias where the
    stub layer differs from the corridor layer. Scans corridor positions."""
    nc = net.GetNetCode()
    tw = mm(tw_mm)
    x1, y1 = p1
    x2, y2 = p2

    def candidates(a1, a2):
        lo, hi = min(a1, a2), max(a1, a2)
        mid = (a1 + a2) / 2
        vals = [a1, a2]     # exact endpoints first: zero-length stubs
        vals += [mid + mm(k * 0.4) * s for k in range(0, 14) for s in (1, -1)]
        vals += [lo - mm(k * 0.4) for k in range(1, 12)]
        vals += [hi + mm(k * 0.4) for k in range(1, 12)]
        return vals

    for horiz in (abs(x2 - x1) >= abs(y2 - y1), abs(x2 - x1) < abs(y2 - y1)):
        for lay in (l1, pcbnew.B_Cu if l1 == pcbnew.F_Cu else pcbnew.F_Cu):
            cands = candidates(y1, y2) if horiz else candidates(x1, x2)
            for cc in cands:
                if horiz:
                    c1, c2 = (x1, cc), (x2, cc)
                else:
                    c1, c2 = (cc, y1), (cc, y2)
                v1 = lay != l1
                v2 = lay != l2
                ok = seg_clear(model, c1[0], c1[1], c2[0], c2[1], lay, nc, tw / 2)
                if ok and (x1, y1) != c1:
                    ok = seg_clear(model, x1, y1, c1[0], c1[1], l1, nc, tw / 2)
                if ok and (x2, y2) != c2:
                    ok = seg_clear(model, x2, y2, c2[0], c2[1], l2, nc, tw / 2)
                if ok and v1:
                    ok = via_clear(model, c1[0], c1[1], nc)
                if ok and v2:
                    ok = via_clear(model, c2[0], c2[1], nc)
                if not ok:
                    continue
                for (ax, ay, bx, by, pl) in [
                        (x1, y1, c1[0], c1[1], l1),
                        (x2, y2, c2[0], c2[1], l2),
                        (c1[0], c1[1], c2[0], c2[1], lay)]:
                    if (ax, ay) != (bx, by):
                        add_track(b, model, ax, ay, bx, by, pl, net, tw)
                if v1:
                    add_via(b, model, c1[0], c1[1], net)
                if v2:
                    add_via(b, model, c2[0], c2[1], net)
                return (f"{'H' if horiz else 'V'}/"
                        f"{'F' if lay == pcbnew.F_Cu else 'B'} at "
                        f"{round(cc / 1e6, 2)}")
    return None


def item_layer(b, net, x_mm, y_mm):
    """Find the copper layer of the pad nearest (x,y) on this net."""
    best = None
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() != net:
                continue
            d = math.hypot(p.GetPosition().x - mm(x_mm),
                           p.GetPosition().y - mm(y_mm))
            if best is None or d < best[0]:
                if p.HasHole():
                    lay = pcbnew.B_Cu   # reachable on both; prefer B
                else:
                    lay = pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu
                best = (d, lay)
    return best[1] if best else pcbnew.F_Cu


for attempt in range(3):
    pairs = unconnected_pairs()
    if not pairs:
        break
    print(f"phase1c[{attempt}]: {len(pairs)} unrouted links to repair")
    b = load()
    model = build_model(b)
    fixed = 0
    for net_name, p1, p2 in pairs:
        net = b.FindNet(net_name)
        if net is None:
            continue
        l1 = item_layer(b, net_name, *p1)
        l2 = item_layer(b, net_name, *p2)
        res = try_corridor(b, model, net, (mm(p1[0]), mm(p1[1])),
                           (mm(p2[0]), mm(p2[1])), l1, l2)
        print(f"  {net_name} {p1}->{p2}: {res or 'FAILED'}")
        if res:
            fixed += 1
    save(b)
    if fixed == 0:
        break
print("phase1c: repair loop done")


# ---- phase 2: pours -------------------------------------------------------
b = load()


def zone(bd, net, layer, name, pts, priority=0):
    z = pcbnew.ZONE(bd)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetZoneName(name)
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(mm(0.25))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
    z.SetMinIslandArea(int(8.0 * 1e12))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in pts:
        ch.Append(mm(x), mm(y))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    bd.Add(z)
    return z


full = [(0.4, 0.4), (W - 0.4, 0.4), (W - 0.4, H - 0.4), (0.4, H - 0.4)]
gnd = b.FindNet("GND")
vsys_sw = b.FindNet("VSYS_SW")
zone(b, vsys_sw, pcbnew.B_Cu, "VSYS_SW_B", VSYS_POLY, priority=2)
zone(b, gnd, pcbnew.F_Cu, "GND_F", full)
zone(b, gnd, pcbnew.B_Cu, "GND_B", full)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
save(b)
print("phase2: GND flooded F+B, VSYS_SW pour on B (full pad connection)")


# ---- phase 3: stitch VSYS_SW pads, then GND pads + grid -------------------
def stitch_net(b, model, net_name, grid=None):
    net = b.FindNet(net_name)
    nc = net.GetNetCode()
    tgt = []
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() == nc:
                side = pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu
                tgt.append((p.GetPosition().x, p.GetPosition().y, side))

    def stub_ok(x1, y1, x2, y2):
        return seg_clear(model, x1, y1, x2, y2, None, nc, mm(0.075)) \
            if False else True

    done = fail = 0
    for px, py, side in tgt:
        placed = False
        for r in (0, 0.5, 0.7, 0.9, 1.15, 1.45, 1.85, 2.25, 2.65, 3.1, 3.6, 4.1):
            for a in range(0, 360, 15 if r else 360):
                x = px + mm(r) * math.cos(math.radians(a))
                y = py + mm(r) * math.sin(math.radians(a))
                if not via_clear(model, x, y, nc):
                    continue
                if r and not seg_clear(model, px, py, x, y, side, nc, mm(0.1)):
                    continue
                add_via(b, model, x, y, net)
                if r:
                    add_track(b, model, px, py, x, y, side, net, mm(0.2))
                done += 1
                placed = True
                break
            if placed:
                break
        if not placed:
            fail += 1

    added_grid = 0
    if grid:
        for gx in range(4, int(W) - 3, grid):
            for gy in range(4, int(H) - 3, grid):
                if any(math.hypot(gx - hx, gy - hy) < 3.0 for hx, hy in HOLES):
                    continue
                x, y = mm(gx), mm(gy)
                if via_clear(model, x, y, nc):
                    add_via(b, model, x, y, net)
                    added_grid += 1
    return done, fail, added_grid


b = load()
model = build_model(b)
d, f, _ = stitch_net(b, model, "VSYS_SW")
print(f"phase3a: VSYS_SW stitched {d} pads, {f} failed")
d, f, g = stitch_net(b, model, "GND", grid=10)
print(f"phase3b: GND stitched {d} pads ({f} failed) + {g} grid vias")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
save(b)

# ---- phase 4: pour knit loop ----------------------------------------------
# Pour islands cut off by routed copper: cluster (islands + vias + THT pads)
# per pour net, then join secondary clusters to the main one - first by a
# single via where the opposite layer overlaps main fill, else by a Z-route
# between via-able interior points.
def pour_clusters(b, net_name):
    """Clusters of pour copper. Membership: pad/via inside an island joins it;
    vias join their F/B islands. Returns list of {"islands", "pts"} dicts,
    pts = (x, y, on_f, on_b), sorted by pour area, big first."""
    nc = b.FindNet(net_name).GetNetCode()
    isles = []
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetCode() != nc:
            continue
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.IsOnLayer(L):
                continue
            polys = z.GetFilledPolysList(L)
            for i in range(polys.OutlineCount()):
                isles.append((polys.Outline(i), L))
    joins = []          # (x, y, on_f, on_b, r)
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetCode() == nc:
            p = t.GetPosition()
            joins.append((p.x, p.y, True, True, via_radius(t)))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() != nc:
                continue
            pos = p.GetPosition()
            hole = p.HasHole()
            bb = p.GetBoundingBox()
            joins.append((pos.x, pos.y,
                          hole or p.IsOnLayer(pcbnew.F_Cu),
                          hole or p.IsOnLayer(pcbnew.B_Cu),
                          min(bb.GetWidth(), bb.GetHeight()) / 2))
    trks = []
    for t in b.GetTracks():
        if t.GetClass() != "PCB_VIA" and t.GetNetCode() == nc:
            sp, ep = t.GetStart(), t.GetEnd()
            trks.append((sp.x, sp.y, ep.x, ep.y, t.GetWidth() / 2,
                         t.GetLayer()))
    n = len(isles) + len(joins) + len(trks)
    JO, TO = len(isles), len(isles) + len(joins)
    uf = UF(n)
    tol = mm(0.02)
    boxes = [ch.BBox() for ch, L in isles]
    for i, (ch, L) in enumerate(isles):
        bx = boxes[i]

        def inside(x, y):
            if not (bx.GetLeft() <= x <= bx.GetRight()
                    and bx.GetTop() <= y <= bx.GetBottom()):
                return False
            return ch.PointInside(pcbnew.VECTOR2I(int(x), int(y)))

        for j, (x, y, onf, onb, r) in enumerate(joins):
            on = onf if L == pcbnew.F_Cu else onb
            if on and inside(x, y):
                uf.union(i, JO + j)
        for j, (x1, y1, x2, y2, w, tL) in enumerate(trks):
            if tL != L:
                continue
            if inside(x1, y1) or inside(x2, y2) \
                    or inside((x1 + x2) / 2, (y1 + y2) / 2):
                uf.union(i, TO + j)
    for i in range(len(joins)):
        xi, yi = joins[i][0], joins[i][1]
        for j in range(i + 1, len(joins)):
            if math.hypot(xi - joins[j][0], yi - joins[j][1]) < \
                    joins[i][4] + joins[j][4] + tol:
                uf.union(JO + i, JO + j)
    for i, (x1, y1, x2, y2, w, tL) in enumerate(trks):
        for j in range(i + 1, len(trks)):
            o = trks[j]
            if o[5] == tL and seg_seg_dist((x1, y1, x2, y2), o[:4]) < \
                    w + o[4] + tol:
                uf.union(TO + i, TO + j)
        for j, (x, y, onf, onb, r) in enumerate(joins):
            on = onf if tL == pcbnew.F_Cu else onb
            if on and seg_pt_dist(x1, y1, x2, y2, x, y) < w + r + tol:
                uf.union(TO + i, JO + j)
    groups = {}
    for i, (ch, L) in enumerate(isles):
        g = groups.setdefault(uf.find(i), {"islands": [], "pts": []})
        g["islands"].append((ch, L))
    for j, (x, y, onf, onb, r) in enumerate(joins):
        g = groups.setdefault(uf.find(JO + j),
                              {"islands": [], "pts": []})
        g["pts"].append((x, y, onf, onb))
    for j, (x1, y1, x2, y2, w, tL) in enumerate(trks):
        g = groups.setdefault(uf.find(TO + j),
                              {"islands": [], "pts": []})
        onf = tL == pcbnew.F_Cu
        g["pts"].append((x1, y1, onf, not onf))
        g["pts"].append((x2, y2, onf, not onf))
    out = list(groups.values())
    out.sort(key=lambda g: sum(abs(ch.Area()) for ch, L in g["islands"]),
             reverse=True)
    return out


def interior_points(ch, step_mm=1.0):
    bx = ch.BBox()
    for x in range(bx.GetLeft(), bx.GetRight(), mm(step_mm)):
        for y in range(bx.GetTop(), bx.GetBottom(), mm(step_mm)):
            if ch.PointInside(pcbnew.VECTOR2I(int(x), int(y))):
                yield (x, y)


def suppress_island(b, ch, L):
    """No-pour rule area with the island's own outline: refill deletes it."""
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName("island_prune")
    z.SetLayer(L)
    for setter in ("SetDoNotAllowCopperPour", "SetDoNotAllowZoneFills"):
        if hasattr(z, setter):
            getattr(z, setter)(True)
            break
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.Outline().AddOutline(ch)
    b.Add(z)


def knit_pour(b, model, net_name):
    clusters = pour_clusters(b, net_name)
    if len(clusters) <= 1:
        return 0, 0
    net = b.FindNet(net_name)
    nc = net.GetNetCode()
    main = clusters[0]
    main_boxes = [(ch, ch.BBox(), L) for ch, L in main["islands"]]
    fixed = failed = 0
    for cl in clusters[1:]:
        done = False
        # strategy 1: one via where the opposite layer is main-cluster fill
        for ch, L in cl["islands"]:
            other = pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu
            mains = [(mch, mbx) for (mch, mbx, mL) in main_boxes if mL == other]
            for (x, y) in interior_points(ch):
                for mch, mbx in mains:
                    if not (mbx.GetLeft() <= x <= mbx.GetRight()
                            and mbx.GetTop() <= y <= mbx.GetBottom()):
                        continue
                    if mch.PointInside(pcbnew.VECTOR2I(int(x), int(y))) \
                            and via_clear(model, x, y, nc):
                        add_via(b, model, x, y, net)
                        print(f"  {net_name} island via at "
                              f"({round(x/1e6,1)},{round(y/1e6,1)})")
                        done = True
                        break
                if done:
                    break
            if done:
                break
        # strategy 2: Z-route from island interiors / cluster pads / vias
        if not done:
            cand_src = []
            for (x, y, onf, onb) in cl["pts"]:
                cand_src.append((x, y, pcbnew.F_Cu if onf else pcbnew.B_Cu))
            for ch, L in cl["islands"]:
                for (x, y) in interior_points(ch):
                    cand_src.append((x, y, L))
            cand_dst = [(x, y) for (x, y, _, _) in main["pts"]][:500]
            best = []
            for (x, y, L) in cand_src:
                for (tx, ty) in cand_dst:
                    best.append(((x - tx) ** 2 + (y - ty) ** 2,
                                 (x, y, L), (tx, ty)))
            best.sort(key=lambda e: e[0])
            for _, (x, y, L), (tx, ty) in best[:60]:
                res = try_corridor(b, model, net, (x, y), (tx, ty),
                                   L, pcbnew.F_Cu, 0.5)
                if not res:
                    res = try_corridor(b, model, net, (x, y), (tx, ty),
                                       L, pcbnew.B_Cu, 0.5)
                if res:
                    print(f"  {net_name} bridge ({round(x/1e6,1)},"
                          f"{round(y/1e6,1)})->({round(tx/1e6,1)},"
                          f"{round(ty/1e6,1)}): {res}")
                    done = True
                    break
        if done:
            fixed += 1
            continue
        # strategy 3: island carries no pads/vias -> suppress it entirely
        if not cl["pts"] and cl["islands"]:
            for ch, L in cl["islands"]:
                suppress_island(b, ch, L)
            print(f"  {net_name} empty island suppressed at "
                  f"({round(cl['islands'][0][0].BBox().Centre().x/1e6,1)},"
                  f"{round(cl['islands'][0][0].BBox().Centre().y/1e6,1)})")
            fixed += 1
            continue
        where = (cl["islands"][0][0].BBox().Centre() if cl["islands"]
                 else pcbnew.VECTOR2I(int(cl["pts"][0][0]),
                                      int(cl["pts"][0][1])))
        print(f"  {net_name} cluster at ({round(where.x/1e6,1)},"
              f"{round(where.y/1e6,1)}): FAILED")
        failed += 1
    return fixed, failed


for rnd in range(8):
    b = load()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    model = build_model(b)
    total_fix = total_fail = 0
    for nname in ("GND", "VSYS_SW"):
        fx, fl = knit_pour(b, model, nname)
        total_fix += fx
        total_fail += fl
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    save(b)
    print(f"phase4[{rnd}]: bridged {total_fix}, failed {total_fail}")
    if total_fix == 0:
        break

# ---- phase 4b0: bespoke USB-area fixes -------------------------------------
# Two links the generic Z-router cannot thread (hand-derived, clearance-checked
# against the routed board): the J1 VBUS pads' escape to U3-5 around the shell
# locating pegs, and the USB_DP pad drop onto its already-routed run.
b = load()
# The generic phase-1c repairs park A6<->B6 / A7<->B7 jogs across the only
# USB escape corridors. Rip both jogs out and rebuild the area explicitly:
# both USB_DP pads drop south onto the routed DP run; USB_DM uses the north
# band (B7 feed stub down to its routed run at (75.75,4.66) + A7 jog).
def del_box(net_name, x1, y1, x2, y2):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" or t.GetNetname() != net_name \
                or t.IsLocked():
            continue
        s, e = t.GetStart(), t.GetEnd()
        if all(mm(x1) < v < mm(x2) for v in (s.x, e.x)) and \
                all(mm(y1) < v < mm(y2) for v in (s.y, e.y)):
            b.Delete(t)
            n += 1
    return n


def add_seg(net_name, x1, y1, x2, y2, w=0.2, lay=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(w))
    t.SetLayer(lay)
    t.SetNet(b.FindNet(net_name))
    b.Add(t)


n1 = del_box("USB_DM", 74.4, 6.8, 76.1, 8.3)      # A7<->B7 south jog
n2 = del_box("USB_DM", 74.4, 5.4, 76.1, 7.0)      # A7<->B7 north jog
n3 = del_box("USB_DP", 74.0, 5.4, 75.5, 7.0)      # A6<->B6 north jog
add_seg("USB_DM", 75.75, 6.87, 75.75, 4.66)       # B7 feed stub
add_seg("USB_DM", 74.75, 6.87, 74.75, 5.0)        # A7 north stub
add_seg("USB_DM", 74.75, 5.0, 75.75, 5.0)         # A7 -> B7 feed
add_seg("USB_DP", 74.25, 6.87, 74.25, 9.75)       # B6 south descent
print(f"phase4b0: USB jogs rebuilt (deleted {n1}+{n2}+{n3} segs)")

model = build_model(b)
BESPOKE = [
    # J1 VBUS pads -> U3-5, ducking under the east-west F runs on B.Cu
    ("VBUS", 0.25,
     [(77.4, 6.87, 77.4, 6.3, pcbnew.F_Cu),
      (77.4, 6.3, 76.9, 5.7, pcbnew.F_Cu),
      (76.9, 5.7, 76.9, 5.3, pcbnew.F_Cu),
      (76.9, 5.3, 76.9, 4.2, pcbnew.B_Cu),
      (76.9, 4.2, 83.5, 4.2, pcbnew.B_Cu),
      (83.5, 4.2, 83.5, 3.9, pcbnew.F_Cu)],
     [(76.9, 5.3), (83.5, 4.2)]),
    # USB_DP pad A6 straight down onto its routed run
    ("USB_DP", 0.2, [(75.25, 6.87, 75.25, 9.75, pcbnew.F_Cu)], []),
]
for net_name, w, segs_, vias_ in BESPOKE:
    net = b.FindNet(net_name)
    if net is None:
        continue
    nc = net.GetNetCode()
    ok = all(seg_clear(model, mm(x1), mm(y1), mm(x2), mm(y2), lay, nc,
                       mm(w / 2), m=mm(0.18))
             for (x1, y1, x2, y2, lay) in segs_)
    ok = ok and all(via_clear(model, mm(x), mm(y), nc, m=mm(0.18))
                    for (x, y) in vias_)
    if not ok:
        print(f"phase4b0: {net_name} bespoke path BLOCKED - skipped")
        continue
    for (x1, y1, x2, y2, lay) in segs_:
        add_track(b, model, mm(x1), mm(y1), mm(x2), mm(y2), lay, net, mm(w))
    for (x, y) in vias_:
        add_via(b, model, mm(x), mm(y), net)
    print(f"phase4b0: {net_name} bespoke path added")
save(b)


# ---- phase 4b: DRC-driven signal repair (non-zone leftovers) ---------------
for rnd in range(3):
    pairs = unconnected_pairs()
    if not pairs:
        print(f"phase4b[{rnd}]: no signal leftovers")
        break
    print(f"phase4b[{rnd}]: {len(pairs)} leftovers")
    b = load()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    model = build_model(b)
    fixed = 0
    for net_name, p1, p2 in pairs:
        net = b.FindNet(net_name)
        if net is None:
            continue
        l1 = item_layer(b, net_name, *p1)
        l2 = item_layer(b, net_name, *p2)
        res = try_corridor(b, model, net, (mm(p1[0]), mm(p1[1])),
                           (mm(p2[0]), mm(p2[1])), l1, l2)
        print(f"  {net_name} {p1}->{p2}: {res or 'FAILED'}")
        if res:
            fixed += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    save(b)
    if fixed == 0:
        break


# ---- phase 5: shrink any widened power segment DRC still dislikes ---------
for rnd in range(3):
    out = os.path.join(tempfile.gettempdir(), "v3_drc.json")
    subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error",
                    "--format", "json", "-o", out, B], capture_output=True)
    rep = json.load(open(out))
    todo = []
    for v in rep.get("violations", []):
        if v["type"] != "clearance":
            continue
        for it in v.get("items", []):
            if it["description"].startswith("Track"):
                todo.append((it["pos"]["x"], it["pos"]["y"],
                             it["description"]))
    if not todo:
        print(f"phase5[{rnd}]: no clearance violations left")
        break
    b = load()
    power = {b.FindNet(n).GetNetCode() for n in POWER_NETS if b.FindNet(n)}
    shrunk = 0
    for x, y, desc in todo:
        best = None
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA" or t.GetNetCode() not in power:
                continue
            if t.GetWidth() <= mm(0.2):
                continue
            d = seg_pt_dist(t.GetStart().x, t.GetStart().y,
                            t.GetEnd().x, t.GetEnd().y, mm(x), mm(y))
            if best is None or d < best[0]:
                best = (d, t)
        if best and best[0] < mm(1.0):
            best[1].SetWidth(mm(0.2))
            shrunk += 1
    print(f"phase5[{rnd}]: shrank {shrunk} widened segments")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    save(b)
    if shrunk == 0:
        break

# ---- final refill ---------------------------------------------------------
b = load()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
save(b)
print("final: refill done")

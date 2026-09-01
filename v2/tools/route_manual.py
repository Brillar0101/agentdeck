#!/usr/bin/env python3
"""Hand-routed corridors the autorouter and finish_v2 repair loop could not
close. Each route is a net name, a track width and an ordered waypoint list;
a waypoint is (x, y, layer). A layer change between consecutive waypoints at
the same (x, y) adds a via. Coordinates in mm. Re-fills zones and saves.

Run with KiCad python:  .../python3 v2/tools/route_manual.py [board.kicad_pcb]
Then run drc_fix.py / kicad-cli drc to verify.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
B = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "AgentDeckV2.kicad_pcb")
mm = pcbnew.FromMM
F, Bc = pcbnew.F_Cu, pcbnew.B_Cu

ROUTES = []   # filled in by route_manual_data.py (kept separate so it is easy to edit)
sys.path.insert(0, HERE)
from route_manual_data import ROUTES  # noqa: E402


def add_track(b, net, x1, y1, x2, y2, layer, w):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(w))
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)


def add_via(b, net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.6))
    v.SetDrill(mm(0.3))
    v.SetLayerPair(F, Bc)
    v.SetNet(net)
    b.Add(v)


def main():
    b = pcbnew.LoadBoard(B)
    n_t = n_v = 0
    for net_name, w, pts in ROUTES:
        net = b.FindNet(net_name)
        if net is None:
            raise SystemExit(f"no net {net_name}")
        for (x1, y1, l1), (x2, y2, l2) in zip(pts, pts[1:]):
            if l1 != l2:
                if (x1, y1) != (x2, y2):
                    raise SystemExit(f"{net_name}: layer change must be at the same point")
                add_via(b, net, x1, y1)
                n_v += 1
            else:
                add_track(b, net, x1, y1, x2, y2, l1, w)
                n_t += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(B, b)
    print(f"route_manual: added {n_t} tracks, {n_v} vias -> {B}")


main()

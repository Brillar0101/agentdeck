#!/usr/bin/env python3
"""Export a Specctra DSN for freerouting with GND and VSYS_SW excluded.

V1 routing lore (docs/DESIGN.md): exclude the giant GND net (and here also the
LED VSYS_SW rail, which becomes a B.Cu pour) from the router; those nets are
flooded + via-stitched afterwards by finish_v2.py.

Run with KiCad python:  .../python3 v3/tools/export_dsn.py [out.dsn]
"""
import os
import shutil
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BRD = os.path.join(HW, "AgentDeckV2.kicad_pcb")
EXCLUDE = {"GND", "VBUS", "CC2", "CC1"}   # CC1/CC2 pre-routed by place_pcb

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "AgentDeckV2.dsn")
tmp = os.path.join(HW, "_route_copy.kicad_pcb")
shutil.copyfile(BRD, tmp)
for ext in (".kicad_pro",):
    src = BRD.replace(".kicad_pcb", ext)
    if os.path.exists(src):
        shutil.copyfile(src, tmp.replace(".kicad_pcb", ext))

b = pcbnew.LoadBoard(tmp)
orphan = b.FindNet("")
cleared = 0
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() in EXCLUDE:
            pad.SetNet(orphan)
            cleared += 1
doomed = [t for t in b.GetTracks() if t.GetNetname() in EXCLUDE]
locked_vias = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
               for t in doomed if t.GetClass() == "PCB_VIA" and t.IsLocked()]
for t in doomed:
    b.Delete(t)
# fence every deleted locked via on ALL copper layers - the router cannot see
# them once their net is cleared, and through-vias block inner layers too
for (vx, vy) in locked_vias:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName("locked_via_fence")
    ls = pcbnew.LSET()
    for lay in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(lay)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    poly = z.Outline()
    poly.NewOutline()
    for (x, y) in [(vx-0.75, vy-0.75), (vx+0.75, vy-0.75),
                   (vx+0.75, vy+0.75), (vx-0.75, vy+0.75)]:
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    b.Add(z)
# the battery pocket rule area only forbids FOOTPRINTS on B.Cu, but the DSN
# exporter turns every rule area into a hard routing keepout - drop it here
for z in [z for z in b.Zones() if z.GetZoneName() == "battery_pocket"]:
    b.Delete(z)
# freerouting cannot see the pre-routed CC1/CC2 copper (their nets were
# cleared), so fence the corridors off in the routing copy only
FENCES = [
    (pcbnew.F_Cu, (51.7, 8.55), (58.8, 9.5)),      # CC2 horizontal + stub
    (pcbnew.B_Cu, (46.9, 8.0), (62.1, 9.4)),       # CC1 B.Cu run
    (pcbnew.F_Cu, (60.5, 7.75), (62.0, 9.45)),     # CC1 A5 stub + via
    (pcbnew.F_Cu, (47.0, 7.5), (48.45, 9.45)),     # CC1 R1 stub + via
]
for layer, (x1, y1), (x2, y2) in FENCES:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName("preroute_fence")
    z.SetLayer(layer)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    poly = z.Outline()
    poly.NewOutline()
    for (x, y) in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    b.Add(z)
b.BuildListOfNets()
if not pcbnew.ExportSpecctraDSN(b, out):
    raise SystemExit("DSN export failed")
print(f"cleared {cleared} pads of {sorted(EXCLUDE)}; wrote {out}")
os.remove(tmp)
pro = tmp.replace(".kicad_pcb", ".kicad_pro")
if os.path.exists(pro):
    os.remove(pro)

#!/usr/bin/env python3
"""Export a Specctra DSN for freerouting with GND and VSYS_SW excluded.

V1 routing lore (docs/DESIGN.md): exclude the giant GND net (and here also the
LED VSYS_SW rail, which becomes a B.Cu pour) from the router; those nets are
flooded + via-stitched afterwards by finish_v3.py.

Run with KiCad python:  .../python3 v3/tools/export_dsn.py [out.dsn]
"""
import os
import shutil
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BRD = os.path.join(HW, "ClaudeMicroV3.kicad_pcb")
EXCLUDE = {"GND", "VSYS_SW", "CC2", "CC1"}   # CC1/CC2 pre-routed by place_pcb

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "ClaudeMicroV3.dsn")
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
for t in doomed:
    b.Delete(t)
# the battery pocket rule area only forbids FOOTPRINTS on B.Cu, but the DSN
# exporter turns every rule area into a hard routing keepout - drop it here
for z in [z for z in b.Zones() if z.GetZoneName() == "battery_pocket"]:
    b.Delete(z)
# freerouting cannot see the pre-routed CC1/CC2 copper (their nets were
# cleared), so fence the corridors off in the routing copy only
FENCES = [
    (pcbnew.F_Cu, (66.7, 8.55), (73.8, 9.5)),      # CC2 horizontal + stub
    (pcbnew.B_Cu, (61.9, 8.0), (77.1, 9.4)),       # CC1 B.Cu run
    (pcbnew.F_Cu, (75.5, 7.75), (77.0, 9.45)),     # CC1 A5 stub + via
    (pcbnew.F_Cu, (62.0, 7.5), (63.45, 9.45)),     # CC1 R1 stub + via
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

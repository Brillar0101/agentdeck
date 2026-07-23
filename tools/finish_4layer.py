"""Clean 4-layer finish: reset to routed SES, GND-flood all layers, rebuild keepouts.

Route already places GND/+3V3/VBUS as traces across 4 layers; here In1 becomes the
main ground plane and F/In1/In2/B all get a GND flood for shielding (filling around
the routed traces). +3V3 stays as its routed traces.
"""
import math

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
SES = "/tmp/best4.ses"

b = pcbnew.LoadBoard(B)

# 1. reset: touch footprints FIRST (before any mutation, or SWIG proxies break),
#    then drop tracks and zones so the SES imports cleanly
carriers = [fp for fp in b.GetFootprints()
            if fp.GetReference().startswith(("KEY", "MH"))]
for fp in carriers:
    b.Remove(fp)
for t in list(b.GetTracks()):
    b.Remove(t)
for z in list(b.Zones()):
    b.Remove(z)
pcbnew.SaveBoard(B, b)

# 2. import routed session
b = pcbnew.LoadBoard(B)
if not pcbnew.ImportSpecctraSES(b, SES):
    raise SystemExit("SES import failed")
ntr = len([t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"])
nvi = len([t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"])
print(f"imported {ntr} tracks, {nvi} vias")

# 3. GND flood on all four layers
gnd = b.FindNet("GND")
for layer, name in [(pcbnew.F_Cu, "GND_F"), (pcbnew.In1_Cu, "GND_In1"),
                    (pcbnew.In2_Cu, "GND_In2"), (pcbnew.B_Cu, "GND_B")]:
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetZoneName(name)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.13))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in [(0.3, 0.3), (89.7, 0.3), (89.7, 89.7), (0.3, 89.7)]:
        ch.Append(mm(x), mm(y))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    b.Add(z)

# 4. mounting-hole keepouts (block copper/tracks/vias, but ALLOW the NPTH pad)
for i, (x, y) in enumerate([(6, 6), (84, 6), (6, 84), (84, 84)], 1):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(f"mh_keepout{i}")
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowFootprints(False)
    z.SetLayerSet(pcbnew.LSET.AllCuMask(4))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for k in range(16):
        a = 2 * math.pi * k / 16
        ch.Append(mm(x + 3.0 * math.cos(a)), mm(y + 3.0 * math.sin(a)))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    b.Add(z)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("GND flooded on 4 layers, keepouts rebuilt, poured")

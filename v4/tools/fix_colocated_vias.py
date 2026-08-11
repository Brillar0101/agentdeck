#!/usr/bin/env python3
"""Delete stitching vias drilled on top of same-net PTH pads.

The stitcher placed 6 GND vias at the exact centres of GND through-hole pads
(U6-7, U4-3, ENC1-C/E, ENC2-C/E). A PTH pad is already a plated hole joining
F.Cu and B.Cu, so the via adds no connection - it only asks the fab to drill
the same spot twice, which is a hole collision, not a cosmetic warning.

Only exact same-net coincidences are removed, so no stitching is lost.

Run with KiCad python:  .../python3 v4/tools/fix_colocated_vias.py [board]
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "ClaudeMicroV4.kicad_pcb")

TOL = pcbnew.FromMM(0.05)

b = pcbnew.LoadBoard(BOARD)

pth = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            pos = p.GetPosition()
            pth.append((pos.x, pos.y, p.GetNetname(),
                        f"{fp.GetReference()}-{p.GetPadName()}"))

killed = 0
for t in list(b.GetTracks()):
    if t.GetClass() != "PCB_VIA":
        continue
    v = t.GetPosition()
    for (px, py, pnet, tag) in pth:
        if abs(v.x - px) <= TOL and abs(v.y - py) <= TOL \
                and t.GetNetname() == pnet:
            print(f"  removing {t.GetNetname()} via at "
                  f"({v.x/1e6:.2f},{v.y/1e6:.2f}) - drilled on {tag}")
            b.Delete(t)
            killed += 1
            break

print(f"removed {killed} co-located via(s)")
if killed:
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print("saved")

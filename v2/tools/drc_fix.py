#!/usr/bin/env python3
"""Post-finish DRC repair: run kicad-cli DRC, delete stitch vias that violate
hole clearance (mounting holes, LED windows, switch posts) and any track
segment that shorts two nets, refill zones, repeat until clean or stuck.

Run with KiCad python:  .../python3 v2/tools/drc_fix.py [board.kicad_pcb]
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
B = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "AgentDeckV2.kicad_pcb")
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
FIX_TYPES = {"hole_clearance", "shorting_items", "clearance"}


def drc():
    out = os.path.join(tempfile.gettempdir(), "v2_drcfix.json")
    subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error", "--format",
                    "json", "-o", out, B], capture_output=True)
    return json.load(open(out))


def nearest(board, x, y, classes):
    best = None
    for t in board.GetTracks():
        if t.GetClass() not in classes:
            continue
        p = t.GetPosition()
        d = (p.x - x) ** 2 + (p.y - y) ** 2
        if t.GetClass() == "PCB_TRACK":
            # distance to segment midpoint is fine for a 1 mm match radius
            m = (t.GetStart() + t.GetEnd())
            d = ((m.x / 2 - x) ** 2 + (m.y / 2 - y) ** 2)
            d = min(d, (t.GetStart().x - x) ** 2 + (t.GetStart().y - y) ** 2,
                    (t.GetEnd().x - x) ** 2 + (t.GetEnd().y - y) ** 2)
        if best is None or d < best[0]:
            best = (d, t)
    return best[1] if best and best[0] < pcbnew.FromMM(1.0) ** 2 else None


for rnd in range(6):
    rep = drc()
    todo = [v for v in rep.get("violations", []) if v["type"] in FIX_TYPES]
    unc = len(rep.get("unconnected_items", []))
    print(f"drc_fix[{rnd}]: {len(todo)} fixable errors, {unc} unconnected")
    if not todo:
        break
    board = pcbnew.LoadBoard(B)
    removed = 0
    for v in todo:
        for it in v.get("items", []):
            desc = it.get("description", "")
            x, y = pcbnew.FromMM(it["pos"]["x"]), pcbnew.FromMM(it["pos"]["y"])
            if desc.startswith("Via"):
                t = nearest(board, x, y, {"PCB_VIA"})
            elif desc.startswith("Track") and v["type"] != "clearance":
                t = nearest(board, x, y, {"PCB_TRACK"})
            elif v["type"] == "clearance" and desc.startswith("Via") and \
                    ("[GND]" in desc or "[VSYS_SW]" in desc):
                t = nearest(board, x, y, {"PCB_VIA"})
            elif desc.startswith("Track") and v["type"] == "clearance":
                t = nearest(board, x, y, {"PCB_TRACK"})
                if t is not None and t.GetWidth() > pcbnew.FromMM(0.2):
                    t.SetWidth(pcbnew.FromMM(0.2))   # shrink instead of delete
                    removed += 1
                    t = None
            else:
                t = None
            if t is not None:
                print(f"  remove {t.GetClass()} [{t.GetNetname()}] at "
                      f"({it['pos']['x']:.2f},{it['pos']['y']:.2f}) for {v['type']}")
                board.Delete(t)
                removed += 1
                break
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(B, board)
    if removed == 0:
        print("drc_fix: nothing removable, stopping")
        break
rep = drc()
errs = [v for v in rep.get("violations", []) if v["severity"] == "error"]
print(f"drc_fix final: {len(errs)} errors, {len(rep.get('unconnected_items', []))} unconnected")
for v in errs[:10]:
    print("  ", v["type"], v["description"][:90])

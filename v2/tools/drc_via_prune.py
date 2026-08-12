#!/usr/bin/env python3
"""Delete unlocked vias implicated in DRC errors, refill, repeat (max 3)."""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

mm = pcbnew.FromMM
HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
B = os.path.join(HW, "AgentDeckV2.kicad_pcb")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def drc_errors():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        rpt = f.name
    subprocess.run([CLI, "pcb", "drc", "-o", rpt, "--format", "json", B],
                   capture_output=True)
    d = json.load(open(rpt))
    os.unlink(rpt)
    errs = [v for v in d["violations"] if v["severity"] == "error"]
    return errs, len(d["unconnected_items"])


for rnd in range(3):
    errs, unconn = drc_errors()
    via_pts = []
    for v in errs:
        for it in v.get("items", []):
            if it.get("description", "").startswith("Via"):
                p = it.get("pos", {})
                if p:
                    via_pts.append((p["x"], p["y"]))
    print(f"round {rnd}: {len(errs)} errors, {unconn} unconnected, "
          f"{len(via_pts)} via culprits")
    if not via_pts:
        break
    b = pcbnew.LoadBoard(B)
    killed = 0
    for t in list(b.GetTracks()):
        if t.GetClass() != "PCB_VIA" or t.IsLocked():
            continue
        x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
        if any(abs(x - vx) < 0.05 and abs(y - vy) < 0.05 for vx, vy in via_pts):
            b.Delete(t)
            killed += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(B, b)
    print(f"  deleted {killed} vias, refilled")
errs, unconn = drc_errors()
print(f"FINAL: {len(errs)} errors, {unconn} unconnected")

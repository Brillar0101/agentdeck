#!/usr/bin/env python3
"""Export the V2 fab package: gerbers, drill, CPL (pos), grouped BOM.

Run with plain python3 (uses kicad-cli, not pcbnew):
  python3 v2/tools/export_fab.py
"""
import csv
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
HW = os.path.join(ROOT, "v2", "hardware")
FAB = os.path.join(ROOT, "v2", "fab")
BRD = os.path.join(HW, "AgentDeckV2.kicad_pcb")
NET = os.path.join(HW, "AgentDeckV2.net")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

# LCSC numbers from v2/PARTS.yaml plus the passives used by the schematic
LCSC = {
    "ESP32-S3-WROOM-1-N8R2": "C2913204",
    "TP4056": None,
    "TYPE-C-31-M-12": "C165948",
    "USBLC6-2SC6": "C7519",
    "ME6211C33": "C82942",
    "SN74AHCT1G125": "C7484",
    "SK6812MINI-E": "C5149201",
    "EC11": "C361165",
    "1N4148W": "C81598",
    "SW_PUSH": "C318884",
    "100nF": "C14663",
    "10uF": "C19702",
    "1uF": "C128624",
    "5.1k": "C23186",
    "10k": "C25804",
    "330R": "C23138",
    "SKQUCAA010": None,     # AliExpress / Newark
    "ChocV1": None,         # hot-swap socket, AliExpress
    "JST-PH-2 LiPo": "C295747",
}

os.makedirs(os.path.join(FAB, "gerbers"), exist_ok=True)

subprocess.run([CLI, "pcb", "export", "gerbers", "-o",
                os.path.join(FAB, "gerbers") + "/", BRD], check=True,
               capture_output=True)
subprocess.run([CLI, "pcb", "export", "drill", "-o",
                os.path.join(FAB, "gerbers") + "/", BRD], check=True,
               capture_output=True)
subprocess.run([CLI, "pcb", "export", "pos", "-o",
                os.path.join(FAB, "AgentDeckV2-CPL.csv"), "--format", "csv",
                "--units", "mm", BRD], check=True, capture_output=True)

s = open(NET).read()
groups = {}
for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\).*?\(value "([^"]+)"\).*?'
                     r'\(footprint "([^"]+)"\)', s, re.S):
    ref, val, fp = m.groups()
    groups.setdefault((val, fp), []).append(ref)

with open(os.path.join(FAB, "AgentDeckV2-BOM.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designators", "Qty", "Value", "Footprint", "LCSC", "Notes"])
    for (val, fp), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        lcsc = LCSC.get(val, "")
        note = "" if lcsc else "not an LCSC line - see v2/PARTS.yaml"
        w.writerow([",".join(sorted(refs)), len(refs), val,
                    fp.split(":")[-1], lcsc or "", note])

n = sum(len(v) for v in groups.values())
print(f"fab package written to v2/fab: gerbers, drill, CPL, BOM ({n} parts, "
      f"{len(groups)} lines)")

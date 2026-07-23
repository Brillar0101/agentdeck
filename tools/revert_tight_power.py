"""Revert widened power segments that violate clearance back to routed width."""
import json
import sys

import pcbnew

PROJ = "/Users/barakaeli/kicad-projects/claude-micro"
BOARD = f"{PROJ}/ClaudeMicro.kicad_pcb"
DRC_JSON = sys.argv[1]
POWER_NETS = {"VBUS", "+3V3"}

d = json.load(open(DRC_JSON))
bad_uuids = set()
for v in d["violations"]:
    if v["type"] == "clearance":
        for i in v.get("items", []):
            bad_uuids.add(i["uuid"])

board = pcbnew.LoadBoard(BOARD)
targets = []
for t in board.GetTracks():
    if t.GetClass() != "PCB_VIA" and t.GetNetname() in POWER_NETS \
            and str(t.m_Uuid.AsString()) in bad_uuids:
        targets.append(t)
for t in targets:
    t.SetWidth(pcbnew.FromMM(0.13))
pcbnew.SaveBoard(BOARD, board)
print(f"reverted {len(targets)} power segments to 0.13mm")

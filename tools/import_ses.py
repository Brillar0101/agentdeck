"""Import the Freerouting .ses result into ClaudeMicro.kicad_pcb, refill zones, save."""
import sys

import pcbnew

PROJ = "/Users/barakaeli/kicad-projects/claude-micro"
BOARD = f"{PROJ}/ClaudeMicro.kicad_pcb"
SES = f"{PROJ}/ClaudeMicro.ses"

board = pcbnew.LoadBoard(BOARD)
if not pcbnew.ImportSpecctraSES(board, SES):
    print("ERROR: ImportSpecctraSES failed")
    sys.exit(1)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())

pcbnew.SaveBoard(BOARD, board)
tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
print(f"OK: imported {len(tracks)} track segments, {len(vias)} vias; zones refilled; board saved")

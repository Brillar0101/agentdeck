"""Post-route finishing: import .ses, widen power traces, refill zones, save."""
import pcbnew

PROJ = "/Users/barakaeli/kicad-projects/claude-micro"
BOARD = f"{PROJ}/ClaudeMicro.kicad_pcb"
SES = f"{PROJ}/ClaudeMicro.ses"
POWER_NETS = {"VBUS", "+3V3"}
POWER_W = pcbnew.FromMM(0.25)

board = pcbnew.LoadBoard(BOARD)
if not pcbnew.ImportSpecctraSES(board, SES):
    raise SystemExit("ERROR: ImportSpecctraSES failed")

# Phase 1: gather (no mutation during iteration — SWIG dispatch breaks otherwise)
power_tracks = []
n_seg = n_via = 0
for t in board.GetTracks():
    cls = t.GetClass()
    if cls == "PCB_VIA":
        n_via += 1
        continue
    n_seg += 1
    if t.GetNetname() in POWER_NETS:
        power_tracks.append(t)

# Phase 2: widen power segments
for t in power_tracks:
    t.SetWidth(POWER_W)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(BOARD, board)
print(f"imported: {n_seg} segments, {n_via} vias; widened {len(power_tracks)} power segments to 0.25mm; zones refilled; saved")

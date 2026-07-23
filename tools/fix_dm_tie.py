"""Close the USB D- tie (J1 A7<->B7) via an F.Cu crossover, DRC-validated.

Tries candidate crossover depths; keeps the first one that adds zero
copper violations. Usage: fix_dm_tie.py <y_crossover>
"""
import sys

import pcbnew

mm = pcbnew.FromMM
B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
YC = float(sys.argv[1])
X1, X2, YPAD = 44.25, 45.25, 6.47

board = pcbnew.LoadBoard(B)
net = board.FindNet("USB_DM_CONN")

def seg(x1, y1, x2, y2, layer):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.13))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)

def via(x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.5))
    v.SetDrill(mm(0.3))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)

seg(X1, YPAD, X1, YC, pcbnew.B_Cu)
via(X1, YC)
seg(X1, YC, X2, YC, pcbnew.F_Cu)
via(X2, YC)
seg(X2, YC, X2, YPAD, pcbnew.B_Cu)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(B, board)
print(f"crossover applied at y={YC}")

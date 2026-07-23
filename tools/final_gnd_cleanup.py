"""Remove stitching vias that only chain floating GND islands together, refill.

A via is a useless chain-link if (a) no track touches it and (b) its
connectivity component contains no main-layer fragment. With those vias gone,
zone island removal purges the floating fragments.
"""
import pcbnew

B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
board = pcbnew.LoadBoard(B)
gnd = board.FindNet("GND").GetNetCode()

frags = []
for z in board.Zones():
    if z.GetIsRuleArea() or z.GetNetCode() != gnd:
        continue
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        if not z.IsOnLayer(layer):
            continue
        sps = z.GetFilledPolysList(layer)
        for i in range(sps.OutlineCount()):
            frags.append((layer, sps, i, sps.Outline(i).Area()))

main_idx = set()
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    best = max((k for k, f in enumerate(frags) if f[0] == layer),
               key=lambda k: frags[k][3], default=None)
    if best is not None:
        main_idx.add(best)

gnd_vias = [t for t in board.GetTracks()
            if t.GetClass() == "PCB_VIA" and t.GetNetCode() == gnd]
gnd_tracks = [t for t in board.GetTracks()
              if t.GetClass() != "PCB_VIA" and t.GetNetCode() == gnd]

def frags_at(pos):
    return [k for k, (lay, sps, i, a) in enumerate(frags) if sps.Contains(pos, i)]

parent = list(range(len(frags)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, b):
    parent[find(a)] = find(b)

via_frags = {}
for v in gnd_vias:
    ks = frags_at(v.GetPosition())
    via_frags[id(v)] = ks
    for a, b in zip(ks, ks[1:]):
        union(a, b)

main_roots = {find(k) for k in main_idx}

def via_has_track(v):
    p = v.GetPosition()
    for t in gnd_tracks:
        if t.GetStart() == p or t.GetEnd() == p:
            return True
    return False

removed = 0
for v in gnd_vias:
    ks = via_frags[id(v)]
    if not ks:
        continue
    if all(find(k) not in main_roots for k in ks) and not via_has_track(v):
        board.Remove(v)
        removed += 1
print(f"removed {removed} floating chain-link vias")

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(B, board)
print("refilled and saved")

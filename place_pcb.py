#!/usr/bin/env python3
"""Populate ClaudeMicro.kicad_pcb from the netlist and place footprints.

Run with KiCad's bundled python (has pcbnew):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 place_pcb.py

Front: 12 Choc switches (sockets on back), EC11 dial, 5-way joystick,
touch electrode, 3 aux LEDs. Back: RP2040 core, USB-C (top edge), flash,
crystal, LDO, level shifter, TTP223, BOOTSEL, SWD pads, passives, and the
6 reverse-mount SK6812MINI-E under the agent keys.

Grid: control cells on Choc-ish 18mm pitch; columns x=18/36/54/72,
rows y=20/37/54/71 (matches the Codex Micro's layout reading).
"""
import os
import re
import pcbnew

H = os.path.expanduser("~/kicad-projects/claude-micro")
FPD = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LIB = {"JLC": f"{H}/JLC.pretty",
       "ClaudeMicro": f"{H}/ClaudeMicro.pretty",
       "Resistor_SMD": f"{FPD}/Resistor_SMD.pretty",
       "Capacitor_SMD": f"{FPD}/Capacitor_SMD.pretty"}
NET = f"{H}/ClaudeMicro.net"
BRD = f"{H}/ClaudeMicro.kicad_pcb"

C = {1: 18.0, 2: 36.0, 3: 54.0, 4: 72.0}
R_ = {1: 20.0, 2: 37.0, 3: 54.0, 4: 71.0}
LED_DY = 4.7          # SK6812 window offset south of switch center


def parse_netlist(path):
    s = open(path).read()
    comps = {}
    for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\).*?\(footprint "([^"]+)"\)', s, re.S):
        comps[m.group(1)] = m.group(2)
    nets = {}
    starts = [m.start() for m in re.finditer(r'\(net\s+\(code', s)]
    starts.append(len(s))
    for a, b in zip(starts, starts[1:]):
        chunk = s[a:b]
        nm = re.search(r'\(name "([^"]*)"', chunk)
        name = nm.group(1) if nm else ""
        nodes = re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"', chunk)
        if name and nodes:
            nets[name] = nodes
    return comps, nets


def mm(v):
    return pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1]))


# ---- placement: ref -> (x, y, deg, back?) ----
layout = {}
# switches (sockets flip to back automatically via the back flag)
key_pos = {
    1: (C[2], R_[1]), 2: (C[3], R_[1]),
    3: (C[1], R_[2]), 4: (C[2], R_[2]), 5: (C[3], R_[2]), 6: (C[4], R_[2]),
    7: (C[1], R_[3]), 8: (C[2], R_[3]), 9: (C[3], R_[3]), 10: (C[4], R_[3]),
    11: (45.0, R_[4]),                 # mic-bar switch, 2u cap spans c2..c3
    12: (C[4], R_[4]),
}
for n, (x, y) in key_pos.items():
    layout[f"SW{n}"] = (x, y, 0, True)
# per-key RGB: D1-6 under agent keys K1-6, D10-15 under command keys K7-12
led_refs = [f"D{i+1}" for i in range(6)] + [f"D{i+10}" for i in range(6)]
led_caps = [f"C{19+i}" for i in range(6)] + [f"C{26+i}" for i in range(6)]
for i, (dref, cref) in enumerate(zip(led_refs, led_caps)):
    kx, ky = key_pos[i + 1]
    layout[dref] = (kx, ky + LED_DY, 0, True)
    layout[cref] = (kx + 6.5, ky + LED_DY, 90, True)
# row-4 LED caps hug their LEDs tightly so three wide routing corridors
# stay open into the key field: west x20-40, mid x47-70, east x77-84
layout["C30"] = (40.0, 75.7, 90, True)   # K11 mic-bar LED cap
layout["C31"] = (77.5, 75.7, 90, True)   # K12 LED cap
# front controls
layout["ENC1"] = (C[1], R_[1], 0, False)
layout["JS1"] = (C[4], R_[1], 0, False)
layout["TP1"] = (14.5, R_[4], 0, False)
for i in range(3):
    layout[f"D{7+i}"] = (5.5, 62.0 + i * 4.5, 90, False)     # aux LEDs, front
    layout[f"R{10+i}"] = (5.5, 62.0 + i * 4.5, 90, True)     # their resistors, back
# back: core cluster in the bottom strip (y 76..88 clear of sockets)
back_major = {
    "J1": (45.0, 4.0, 0),      # USB-C at top edge
    "U6": (57.0, 8.0, 0),      # ESD near connector
    "R3": (63.0, 5.0, 90), "R4": (66.0, 5.0, 90),
    "R1": (32.0, 5.0, 90), "R2": (29.0, 5.0, 90),
    "U1": (45.0, 84.0, 0),     # RP2040 in the bottom strip
    "Y1": (29.0, 84.0, 0),     # crystal
    "U2": (64.0, 84.0, 0),     # QSPI flash
    "U3": (13.0, 86.5, 0),     # LDO
    "U4": (21.0, 8.0, 0),      # level shifter in the top strip (clears lane 1)
    "C25": (17.0, 8.0, 90),
    "R9": (25.5, 8.0, 0),
    "U5": (13.0, 74.5, 0),     # TTP223 right under its electrode
    "C3": (8.0, 74.5, 90), "C4": (18.0, 74.5, 90),
    "SW13": (81.0, 83.0, 0),   # BOOTSEL
    "J2": (25.0, 87.8, 0),     # SWD pads
    # RP2040 decoupling ring (clear of the D14/D15 LED band at y~75.7)
    "C5": (37.0, 79.0, 0), "C6": (41.0, 79.0, 0), "C7": (49.0, 79.0, 0),
    "C8": (53.0, 79.0, 0), "C9": (37.0, 88.4, 0), "C10": (41.0, 88.4, 0),
    "C11": (49.0, 88.4, 0), "C12": (53.0, 88.4, 0),
    "C13": (52.5, 80.8, 0), "C14": (34.0, 84.0, 90),
    "C15": (64.0, 78.3, 0),
    "C16": (6.5, 82.5, 90), "C17": (19.5, 82.5, 90),
    "R5": (28.0, 80.5, 0),
    "C1": (24.5, 84.0, 90), "C2": (31.5, 80.5, 0),  # crystal load caps
    "R8": (33.0, 88.4, 0),
    "R6": (70.0, 88.5, 0), "R7": (74.5, 88.5, 0),
}
for ref, (x, y, d) in back_major.items():
    layout[ref] = (x, y, d, True)


def main():
    import shutil
    comps, nets = parse_netlist(NET)
    shutil.copyfile(f"{H}/board_outline.kicad_pcb", BRD)
    board = pcbnew.LoadBoard(BRD)

    placed = {}
    for ref, fpid in comps.items():
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(LIB[lib], name)
        if fp is None:
            print("MISSING FP:", fpid)
            continue
        fp.SetReference(ref)
        if ref not in layout:
            print("NO PLACEMENT:", ref)
        x, y, deg, back = layout.get(ref, (45.0, 45.0, 0, True))
        board.Add(fp)
        fp.SetPosition(mm((x, y)))
        if back:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        fp.SetOrientationDegrees(deg)
        fp.Reference().SetVisible(False)
        if ref == "J1" and hasattr(fp, "SetLocalClearance"):
            fp.SetLocalClearance(pcbnew.FromMM(0.09))   # factory fp geometry
        placed[ref] = fp

    made = 0
    for name, nodes in nets.items():
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
        for ref, padnum in nodes:
            fp = placed.get(ref)
            if not fp:
                continue
            for pad in fp.Pads():
                if pad.GetNumber() == padnum:
                    pad.SetNet(ni)
        made += 1

    add_silk(board)
    add_stitching(board)
    add_pours(board)

    board.BuildListOfNets()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(BRD, board)
    print(f"placed {len(placed)} footprints, {made} nets, "
          f"{len(list(board.Zones()))} zones")


def text(board, t, x, y, size, layer, thick, angle=0, mirror=False):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(t)
    tx.SetPosition(mm((x, y)))
    tx.SetLayer(layer)
    tx.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    tx.SetTextThickness(pcbnew.FromMM(thick))
    if angle:
        tx.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    if mirror:
        tx.SetMirrored(True)
    board.Add(tx)


def add_silk(board):
    F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
    # touch dot ring + label
    ring = pcbnew.PCB_SHAPE(board)
    ring.SetShape(pcbnew.SHAPE_T_CIRCLE)
    ring.SetCenter(mm((14.5, R_[4])))
    ring.SetEnd(mm((14.5 + 7.0, R_[4])))
    ring.SetLayer(F)
    ring.SetWidth(pcbnew.FromMM(0.25))
    board.Add(ring)
    text(board, "touch", 14.5, 80.5, 0.9, F, 0.15)
    # up arrow (orientation hint, like the original)
    text(board, "^", 45.0, 11.0, 2.2, F, 0.35)
    # identity
    text(board, "CLAUDE MICRO", 45.0, 87.0, 2.0, F, 0.35)
    text(board, "princetekki.com", 45.0, 89.5, 0.9, F, 0.15)
    # back: flash + battery-free + id
    text(board, "FLASH: hold BOOT · replug USB", 45.0, 92.0 - 20.0, 1.0, B, 0.16, mirror=True)
    text(board, "ClaudeMicro v0.1 · OSHW · github.com/Brillar0101", 45.0, 75.0, 1.0, B, 0.16, mirror=True)
    text(board, "BOOT", 81.0, 79.0, 0.9, B, 0.15, mirror=True)


def _via(board, pos, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pos)
    v.SetWidth(pcbnew.FromMM(0.6))
    v.SetDrill(pcbnew.FromMM(0.3))
    v.SetNet(net)
    board.Add(v)


def add_stitching(board):
    gnd = board.FindNet("GND")
    for (x, y) in [(4.0, 45.0), (86.0, 45.0), (45.0, 45.5), (10.0, 10.0),
                   (80.0, 10.0), (10.0, 55.0), (80.0, 55.0), (28.0, 62.0),
                   (62.0, 62.0), (45.0, 28.5)]:
        _via(board, mm((x, y)), gnd)


def add_pours(board):
    gnd = board.FindNet("GND")
    pts = [(0.6, 0.6), (89.4, 0.6), (89.4, 89.4), (0.6, 89.4)]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetAssignedPriority(0)
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
        z.SetMinIslandArea(int(3.0 * 1e12))
        poly = z.Outline()
        poly.NewOutline()
        for (x, y) in pts:
            poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        z.SetIsFilled(False)
        board.Add(z)


main()

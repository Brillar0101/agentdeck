#!/usr/bin/env python3
"""Populate v2/hardware/AgentDeckV2.kicad_pcb from the netlist and place parts.

Ported from the V3 placer. Run with KiCad's bundled python (pcbnew):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/\
Current/bin/python3 v2/tools/place_pcb.py

Board: 112x112 mm, rounded corners r=6, y down, origin top-left.
  - key grid 4 rows x 5 cols, 18.7 x 19.3 pitch (V1 spacing):
    cols x=18.6..93.4, rows y=42..99.9
  - top strip (y<33): ESP32-S3 top-left (antenna overhangs the top edge),
    USB-C top centre, ST7789V LCD pad row below it (glass area marked),
    EC11 left of USB, SKQUCAA010 joystick right, power cluster top-right
  - battery: 103450 cell (34x50) lives in the case tray under the key
    field; Dwgs marker only - sockets sit above the cell, foam between
  - LEDs reverse-mount on B.Cu at key +(0,+4.8), matrix diode B.Cu at
    key +(-5,-6), per-LED 100nF B.Cu at key +(-4.6,+4.8)
"""
import os
import re

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))          # repo root
HW = os.path.join(ROOT, "v2", "hardware")
NET = os.path.join(HW, "AgentDeckV2.net")
BRD = os.path.join(HW, "AgentDeckV2.kicad_pcb")
V1_SHAPES = os.path.join(ROOT, "v1", "hardware", "JLC.3dshapes")
FPD = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LIB = {
    "JLC": os.path.join(HW, "JLC.pretty"),
    "V3": os.path.join(ROOT, "v3", "hardware", "V3.pretty"),
    "JLC_V1": os.path.join(ROOT, "v1", "hardware", "JLC.pretty"),
    "AgentDeck": os.path.join(ROOT, "v1", "hardware", "AgentDeck.pretty"),
    "Diode_SMD": f"{FPD}/Diode_SMD.pretty",
    "Package_TO_SOT_SMD": f"{FPD}/Package_TO_SOT_SMD.pretty",
    "Resistor_SMD": f"{FPD}/Resistor_SMD.pretty",
    "Capacitor_SMD": f"{FPD}/Capacitor_SMD.pretty",
}

W, H, R = 112.0, 112.0, 6.0
PITCH_X, PITCH_Y = 18.7, 19.3
COLS = [18.6 + PITCH_X * c for c in range(5)]
ROWS = [42.0 + PITCH_Y * r for r in range(4)]
HOLES = [(6, 6), (106, 6), (6, 106), (106, 106)]
BATT = (39.0, 52.0, 73.0, 102.0)       # 34x50 cell marker (cell in case tray)
ANT_KEEPOUT = (10.0, 0.0, 30.0, 0.9)   # copper void under antenna sliver
LCD_GLASS = (42.0, 15.0, 70.0, 29.5)   # panel glass area marker
USB_X = 60.0

mm = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def parse_netlist(path):
    s = open(path).read()
    comps = {}
    for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\).*?\(footprint "([^"]+)"\)',
                         s, re.S):
        comps[m.group(1)] = m.group(2)
    nets = {}
    starts = [m.start() for m in re.finditer(r'\(net\s*\(code', s)]
    starts.append(len(s))
    for a, b in zip(starts, starts[1:]):
        chunk = s[a:b]
        nm = re.search(r'\(name "([^"]*)"', chunk)
        name = nm.group(1) if nm else ""
        nodes = re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"', chunk)
        if name and nodes:
            nets[name] = nodes
    return comps, nets


# ---- placement table: ref -> (x, y, deg, back?) ---------------------------
layout = {
    "U1": (20.0, 9.9, 0, False),        # ESP32-S3, antenna overhangs top edge
    "C1": (12.0, 21.0, 0, False),
    "C2": (16.5, 21.0, 0, False),
    "C3": (21.0, 21.0, 0, False),
    "C4": (25.5, 21.0, 0, False),
    "R9": (7.5, 24.5, 0, False),        # EN pullup
    "R10": (12.5, 24.5, 0, False),      # IO0 pullup
    "C5": (17.5, 24.5, 0, False),       # EN 100nF
    "SW26": (32.0, 28.0, 0, False),     # BOOT
    "SW27": (41.0, 28.0, 0, False),     # RESET
    "J3": (5.5, 50.0, 90, False),       # UART prog pads, left edge
    "ENC1": (39.0, 13.0, 0, False),     # dial left of USB
    "J1": (USB_X, 4.4, 180, False),     # USB-C, mouth over the top edge
    "U3": (68.5, 5.3, 0, False),        # ESD at the connector
    "R1": (49.0, 7.9, 0, False),        # CC1 5.1k
    "R2": (53.0, 7.9, 0, False),        # CC2 5.1k
    "JS1": (86.0, 13.0, 0, False),      # joystick top-right
    # joystick matrix diodes on the back under JS1
    "D21": (80.0, 22.0, 0, True),
    "D22": (85.0, 22.0, 0, True),
    "D23": (90.0, 22.0, 0, True),
    "D24": (82.5, 25.0, 0, True),
    "D25": (87.5, 25.0, 0, True),
    # power cluster, top-right
    "U5": (99.0, 10.0, 0, False),       # ME6211 LDO (VBUS -> 3V3)
    "C6": (94.0, 15.0, 0, False),
    "C7": (103.5, 15.0, 0, False),
    # LED chain head (B.Cu, near LED1 under SW1)
    "U2": (24.0, 35.0, 0, True),
    "C9": (19.5, 37.5, 90, True),
    "R11": (28.0, 33.0, 0, True),
}

# keys, matrix diodes, LEDs (serpentine chain), per-LED caps
for idx in range(20):
    r, c = idx // 5, idx % 5
    kx, ky = COLS[c], ROWS[r]
    layout[f"SW{idx + 1}"] = (kx, ky, 0, False)
    layout[f"D{idx + 1}"] = (kx - 5.0, ky - 6.0, 0, True)
    led_i = r * 5 + (c if r % 2 == 0 else 4 - c)      # serpentine LED order
    layout[f"LED{led_i + 1}"] = (kx, ky + 4.8, 180 if r % 2 else 0, True)
    layout[f"C{12 + led_i}"] = (kx - 4.6, ky + 4.8, 90, True)


def fix_models(fp, fpid):
    """Rebuild 3D model paths (mutating FP_3DMODEL in place doesn't stick)."""
    fixed = []
    for m in fp.Models():
        fn = m.m_Filename
        if fpid.startswith("JLC_V1:") or fpid.startswith("AgentDeck:"):
            fn = fn.replace("${KIPRJMOD}/JLC.3dshapes", V1_SHAPES)
        fixed.append((fn, m.m_Offset, m.m_Rotation, m.m_Scale))
    fp.Models().clear()
    for fn, off, rot, sc in fixed:
        m = pcbnew.FP_3DMODEL()
        m.m_Filename, m.m_Offset, m.m_Rotation, m.m_Scale = fn, off, rot, sc
        fp.Models().push_back(m)


def outline(board):
    pts = [((R, 0), (W - R, 0)), ((W, R), (W, H - R)),
           ((W - R, H), (R, H)), ((0, H - R), (0, R))]
    for (x1, y1), (x2, y2) in pts:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(x1, y1))
        s.SetEnd(V(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
    k = R * (1 - 0.7071067812)
    arcs = [((R, 0), (k, k), (0, R)), ((W - R, 0), (W - k, k), (W, R)),
            ((W, H - R), (W - k, H - k), (W - R, H)),
            ((0, H - R), (k, H - k), (R, H))]
    for a, mid, b in arcs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(V(*a), V(*mid), V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)


def mounting_holes(board):
    for i, (x, y) in enumerate(HOLES, 1):
        fp = pcbnew.FOOTPRINT(board)
        fp.SetFPID(pcbnew.LIB_ID("V2", "MountingHole_M2_5"))
        fp.SetReference(f"MH{i}")
        fp.SetValue("M2.5")
        fp.SetPosition(V(x, y))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
        p = pcbnew.PAD(fp)
        p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(pcbnew.VECTOR2I(mm(2.7), mm(2.7)))
        p.SetDrillSize(pcbnew.VECTOR2I(mm(2.7), mm(2.7)))
        p.SetPosition(V(x, y))
        p.SetLayerSet(p.UnplatedHoleMask())
        p.SetLocalClearance(mm(0.4))
        fp.Add(p)
        board.Add(fp)


def rule_area(board, x1, y1, x2, y2, layers, no_pour=True, no_tracks=False,
              no_vias=True, no_footprints=False, name=""):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    for setter in ("SetDoNotAllowCopperPour", "SetDoNotAllowZoneFills"):
        if hasattr(z, setter):
            getattr(z, setter)(no_pour)
            break
    z.SetDoNotAllowTracks(no_tracks)
    z.SetDoNotAllowVias(no_vias)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(no_footprints)
    poly = z.Outline()
    poly.NewOutline()
    for (x, y) in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
        poly.Append(mm(x), mm(y))
    board.Add(z)


def rect(board, x1, y1, x2, y2, layer, w=0.15):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(V(x1, y1))
    s.SetEnd(V(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def text(board, t, x, y, size, layer, thick, justify=None, angle=0, mirror=False):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(t)
    tx.SetPosition(V(x, y))
    tx.SetLayer(layer)
    tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    tx.SetTextThickness(mm(thick))
    if justify == "left":
        tx.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    elif justify == "right":
        tx.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if angle:
        tx.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    if mirror:
        tx.SetMirrored(True)
    board.Add(tx)


def add_silk(board):
    F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
    text(board, "AgentDeck V2", 8.0, 109.3, 1.6, F, 0.3, justify="left")
    text(board, "FLASH: hold BOOT - tap RST - release BOOT", 60.0, 109.3, 1.0,
         F, 0.16, justify="left")
    text(board, "BOOT", 32.0, 32.2, 1.0, F, 0.16)
    text(board, "RST", 41.0, 32.2, 1.0, F, 0.16)
    text(board, "3V3 TX GND RX", 5.5, 57.5, 1.0, F, 0.16)
    text(board, "USB-C", USB_X, 10.2, 1.0, F, 0.16)
    legend = ["AgentDeckV2  ESP32-S3-WROOM-1",
              "ROW0-3=IO4-7 ROW4(JS)=IO15  COL0-4=IO10-14",
              "LED=IO21  ENC A/B/SW=IO40/41/42",
              "UART TX=IO43 RX=IO44   USB=IO19/20"]
    for i, line in enumerate(legend):
        text(board, line, 56.0, 58.0 + 3.2 * i, 1.2, B, 0.2, mirror=True)


def main():
    comps, nets = parse_netlist(NET)
    board = pcbnew.CreateEmptyBoard()
    board.SetFileName(BRD)
    bds = board.GetDesignSettings()
    bds.SetCopperLayerCount(4)
    bds.m_TrackMinWidth = mm(0.1)
    if hasattr(bds, "m_MinClearance"):
        bds.m_MinClearance = mm(0.13)
    if hasattr(bds, "m_CopperEdgeClearance"):
        bds.m_CopperEdgeClearance = mm(0.3)

    outline(board)

    placed = {}
    missing = []
    for ref, fpid in sorted(comps.items()):
        lib, name = fpid.split(":")
        fp = pcbnew.FootprintLoad(LIB[lib], name)
        if fp is None:
            missing.append(fpid)
            continue
        fp.SetReference(ref)
        r = fp.Reference()
        r.SetVisible(True)
        r.SetTextSize(pcbnew.VECTOR2I(mm(0.7), mm(0.7)))
        r.SetTextThickness(mm(0.11))
        fix_models(fp, fpid)
        if ref == "J1" or ref.startswith("SW"):
            # locating pegs modeled as zero-annulus PTH -> make NPTH
            for pad in fp.Pads():
                if not pad.GetNumber() and pad.HasHole():
                    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
                    pad.SetLayerSet(pad.UnplatedHoleMask())
        if ref not in layout:
            print("NO LAYOUT:", ref)
        x, y, deg, back = layout.get(ref, (56.0, 56.0, 0, False))
        board.Add(fp)
        fp.SetPosition(V(x, y))
        if back:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        fp.SetOrientationDegrees(deg)
        placed[ref] = fp
    if missing:
        raise SystemExit(f"MISSING FOOTPRINTS: {missing}")

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

    def fixed_track(net, x1, y1, x2, y2, layer, w=0.2):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
        t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetLocked(True)
        board.Add(t)

    def locked_via(net, vx, vy):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(vx), int(vy)))
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(net)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetLocked(True)
        board.Add(v)

    # USB fine-pitch escapes freerouting cannot thread (V3 lessons):
    # CC2 out of B5 on F.Cu; CC1 via B.Cu; VBUS pad bridge on B.Cu.
    cc2 = board.FindNet("CC2")
    b5 = next(p for p in placed["J1"].Pads() if p.GetNumber() == "B5")
    r2p = next(p for p in placed["R2"].Pads() if p.GetNumber() == "1")
    bx, by = b5.GetPosition().x, b5.GetPosition().y
    rx, ry = r2p.GetPosition().x, r2p.GetPosition().y
    wy = mm(9.05)
    for (x1, y1), (x2, y2) in zip([(bx, by), (bx, wy), (rx, wy)],
                                  [(bx, wy), (rx, wy), (rx, ry)]):
        fixed_track(cc2, x1, y1, x2, y2, pcbnew.F_Cu)

    cc1 = board.FindNet("CC1")
    a5 = next(p for p in placed["J1"].Pads() if p.GetNumber() == "A5")
    r1p = next(p for p in placed["R1"].Pads() if p.GetNumber() == "1")
    ax, ay = a5.GetPosition().x, a5.GetPosition().y
    r1x, r1y = r1p.GetPosition().x, r1p.GetPosition().y
    cy = mm(8.7)
    fixed_track(cc1, ax, ay, ax, cy, pcbnew.F_Cu)
    fixed_track(cc1, ax, cy, r1x, cy, pcbnew.B_Cu)
    fixed_track(cc1, r1x, cy, r1x, r1y, pcbnew.F_Cu)
    locked_via(cc1, ax, cy)
    locked_via(cc1, r1x, cy)

    vbus = board.FindNet("VBUS")
    pj = {p.GetNumber(): p.GetPosition() for p in placed["J1"].Pads()}
    lx, ly = pj["B4A9"].x, pj["B4A9"].y
    rx2, ry2 = pj["A4B9"].x, pj["A4B9"].y
    by2 = mm(7.9)
    fixed_track(vbus, lx, ly, lx, by2, pcbnew.F_Cu, 0.3)
    fixed_track(vbus, lx, by2, rx2, by2, pcbnew.B_Cu, 0.5)
    fixed_track(vbus, rx2, by2, rx2, ry2, pcbnew.F_Cu, 0.3)
    locked_via(vbus, lx, by2)
    locked_via(vbus, rx2, by2)

    mounting_holes(board)

    rule_area(board, *ANT_KEEPOUT, [pcbnew.F_Cu, pcbnew.B_Cu], no_pour=True,
              no_vias=True, name="antenna_keepout")
    rule_area(board, USB_X - 5.5, 5.9, USB_X + 5.5, 7.6, [pcbnew.F_Cu],
              no_pour=False, no_tracks=False, no_vias=False,
              no_footprints=False, name="usb_area")

    add_silk(board)
    board.BuildListOfNets()
    pcbnew.SaveBoard(BRD, board)

    boxes = []
    for ref, fp in placed.items():
        bb = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        if bb.OutlineCount():
            r = bb.BBox()
            boxes.append((ref, fp.IsFlipped(), r.GetLeft(), r.GetTop(),
                          r.GetRight(), r.GetBottom()))
    n_overlap = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[1] != b[1]:
                continue
            if a[2] < b[4] and b[2] < a[4] and a[3] < b[5] and b[3] < a[5]:
                print(f"COURTYARD OVERLAP: {a[0]} vs {b[0]}")
                n_overlap += 1
    print(f"placed {len(placed)} footprints, {made} nets, "
          f"{n_overlap} courtyard overlaps -> {BRD}")


main()

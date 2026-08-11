#!/usr/bin/env python3
"""Populate v4/hardware/ClaudeMicroV4.kicad_pcb from the netlist and place parts.

Parameterized port of v3/tools/place_pcb.py (the DRC-0 V3 pipeline). Run with
KiCad's bundled python (pcbnew):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/\
Current/bin/python3 v4/tools/place_pcb.py

Board: 150x110 mm, rounded corners r=6, y down, origin top-left. V3 skeleton
(key grid, USB-C, ESP32 antenna overhang, power cluster, battery pocket,
CC1/CC2/VBUS pre-routes) unchanged; V4 deltas:
  - LCD1 1.69" touch LCD module tab replaces OLED1 (glass extends north),
    TP1 and the BOOT/RESET tacts shifted west out from under the glass
  - ENC2 on the left edge at mid-height, J3 prog pads moved down to y=75
  - audio corner (DESIGN-V4 rules 11-14): U6 NS4168 + C36/C37 at (140,60),
    J4 speaker JST at the right edge, MK1 I2S mic in the top strip with a
    0.9mm acoustic port + copper/pour keepout ring (mic_port_void)
"""
import os
import re

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))          # repo root
HW = os.path.join(ROOT, "v4", "hardware")
NET = os.path.join(HW, "ClaudeMicroV4.net")
BRD = os.path.join(HW, "ClaudeMicroV4.kicad_pcb")
V1_SHAPES = os.path.join(ROOT, "hardware", "JLC.3dshapes")
NC_SHAPES = "/Users/barakaeli/Open Source Hardware/NeuralCard/JLC.3dshapes"
FPD = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LIB = {
    "V4": os.path.join(HW, "V4.pretty"),
    "V3": os.path.join(ROOT, "v3", "hardware", "V3.pretty"),
    "JLC_V1": os.path.join(ROOT, "hardware", "JLC.pretty"),
    "ClaudeMicro": os.path.join(ROOT, "hardware", "ClaudeMicro.pretty"),
    "Diode_SMD": f"{FPD}/Diode_SMD.pretty",
    "Connector_JST": f"{FPD}/Connector_JST.pretty",
    "Package_TO_SOT_SMD": f"{FPD}/Package_TO_SOT_SMD.pretty",
    "Resistor_SMD": f"{FPD}/Resistor_SMD.pretty",
    "Capacitor_SMD": f"{FPD}/Capacitor_SMD.pretty",
}

W, H, R = 150.0, 110.0, 6.0
COLS = [30.0 + 18.0 * c for c in range(6)]
ROWS = [40.0 + 18.0 * r for r in range(4)]
HOLES = [(6, 6), (144, 6), (6, 104), (144, 104), (6, 55), (144, 55)]
BATT = (98.0, 0.7, 140.0, 32.7)        # 42x32 pocket, bottom side keep clear
ANT_KEEPOUT = (10.0, 0.0, 30.0, 0.9)   # copper/pour void under antenna sliver
TOUCH_VOID = (31.0, 8.0, 45.0, 22.0)   # no pour under the touch pad (rule 6);
                                       # follows TP1 to (38,15) in V4
MIC_PORT_VOID = (55.0, 14.0, 57.0, 16.0)  # no pour/vias over the mic acoustic
                                          # port at (56,15) (DESIGN-V4 rule 11)

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
    "J1": (75.0, 4.4, 180, False),      # USB-C, mouth over the top edge
    "U3": (83.5, 5.3, 0, False),        # ESD at the connector
    "R1": (63.5, 7.9, 0, False),        # CC1 5.1k (CC1 pre-routed on B.Cu)
    "R2": (68.0, 7.9, 0, False),        # CC2 5.1k
    # LCD module tab (glass extends north over the top strip, rule 13)
    "LCD1": (67.0, 27.6, 0, False),
    "R12": (56.0, 31.0, 0, False),      # SDA pullup
    "R13": (59.5, 31.0, 0, False),      # SCL pullup
    "C10": (63.0, 31.0, 0, False),      # LCD 100nF
    "R14": (66.5, 31.0, 0, False),      # LCD BL series 100R
    "ENC1": (90.0, 16.0, 0, False),
    "ENC2": (13.0, 64.3, 90, False),    # left edge, mid-height (V4); dropped
                                        # below MH5 (6,55): at y=55 the EC11
                                        # D/E pads violate the hole clearance
    "TP1": (38.0, 15.0, 0, False),      # shifted west, out from under the glass
    "SW26": (30.0, 25.5, 0, False),     # BOOT (shifted west of glass)
    "SW27": (40.0, 25.5, 0, False),     # RESET
    "R9": (7.5, 24.5, 0, False),        # EN pullup
    "R10": (12.5, 24.5, 0, False),      # IO0 pullup
    "C5": (17.5, 24.5, 0, False),       # EN 100nF
    # module decoupling, 2mm off the pin row (rule 2). Rotated 90 in V4 so each
    # GND pad points SOUTH into the open pour band instead of being sealed
    # between the COL and +3V3 runs (V4 adds LCD/I2S traffic through this
    # pocket, which stranded C2/C3's GND pads in the V3-style 0-deg row).
    "C1": (12.0, 21.0, 90, False),
    "C2": (16.5, 21.0, 90, False),
    "C3": (21.0, 21.0, 90, False),
    "C4": (25.5, 21.6, 90, False),      # 10uF bulk (0805 is taller than the
                                        # 0603s: +0.6mm south clears U1 p24/25)
    "J3": (6.5, 78.0, 90, False),       # UART prog pads, left edge (below ENC2)
    # audio corner, right side = opposite the antenna (rule 14)
    "U6": (140.0, 60.0, 0, False),      # NS4168, outputs face the right edge
    "C36": (139.5, 55.3, 0, False),     # amp 100nF at VDD (west of MH6 hole)
    "C37": (135.0, 55.3, 0, False),     # amp 22uF bulk (0805)
    "J4": (144.0, 68.0, 90, False),     # speaker JST, wire exits right
    "MK1": (56.0, 15.0, 0, False),      # I2S mic, top strip, >=10mm from SPK
    "C38": (52.0, 18.5, 90, False),     # mic 100nF
    # LED chain head (B.Cu). V4 moves it west into the open left margin: at
    # V3's (24,31) the V4 route seals U2's GND/VSYS_SW pads and C9 inside the
    # U1 pin fan-out, leaving pour islands no copper path can reach.
    "U2": (14.5, 37.0, 0, True),
    "C9": (14.5, 41.5, 90, True),
    "R11": (19.5, 37.0, 0, True),
    # power cluster, top-right (all F.Cu; battery pocket is below the PCB)
    "U4": (106.0, 10.0, 0, False),      # TP4056
    "R3": (105.0, 16.5, 0, False),      # PROG 2.4k
    "C11": (110.5, 16.5, 0, False),     # VBUS 10uF
    "Q1": (116.0, 6.5, 0, False),       # AO3401A load share
    "R6": (116.0, 12.5, 0, False),      # gate bleed 100k
    "D25": (124.0, 5.0, 0, False),      # SS34 VBUS->VSYS
    "U5": (133.0, 9.0, 0, False),       # ME6211 LDO
    "C6": (128.5, 13.0, 0, False),
    "C7": (137.5, 13.0, 0, False),
    "R7": (127.0, 17.0, 0, False),      # VBAT div 100k
    "R8": (132.0, 17.0, 0, False),      # VBAT div 47k
    "C8": (137.0, 17.0, 0, False),
    "J2": (143.5, 25.0, 180, False),    # JST-PH battery, wire exits toward pocket
    "SW25": (147.6, 45.0, 90, False),   # power switch, actuator over right edge
}

# keys, diodes, LEDs (serpentine chain), per-LED caps - V3 pattern verbatim.
for idx in range(24):
    r, c = idx // 6, idx % 6
    kx, ky = COLS[c], ROWS[r]
    layout[f"SW{idx + 1}"] = (kx, ky, 0, False)
    layout[f"D{idx + 1}"] = (kx - 5.0, ky - 6.0, 0, True)
    led_i = r * 6 + (c if r % 2 == 0 else 5 - c)      # serpentine LED order
    layout[f"LED{led_i + 1}"] = (kx, ky + 4.8, 180 if r % 2 else 0, True)
    layout[f"C{12 + led_i}"] = (kx - 4.6, ky + 4.8, 90, True)


def fix_models(fp, fpid):
    """Rewrite 3D model paths that are only valid in their home projects."""
    fixed = []
    for m in fp.Models():
        fn = m.m_Filename
        if fpid.startswith("JLC_V1:"):
            fn = fn.replace("${KIPRJMOD}/JLC.3dshapes", V1_SHAPES)
        if "kicad-projects/NeuralCard" in fn:
            fn = NC_SHAPES + "/" + fn.rsplit("/", 1)[1]
        # KiCad 10 ships no SM4 (boss) variant - use the plain S2B model
        fn = fn.replace("JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
                        "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal")
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
        fp.SetFPID(pcbnew.LIB_ID("V4", "MountingHole_M2_5"))   # FPID must be
        fp.SetReference(f"MH{i}")                              # set: empty FPID
        fp.SetValue("M2.5")                                    # corrupts SES
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
    text(board, "ClaudeMicro V4 - princetekki.com", 24.0, 106.3, 1.6, F, 0.3,
         justify="left")
    text(board, "FLASH: hold BOOT - tap RST - release BOOT", 88.0, 105.3, 1.0,
         F, 0.16, justify="left")
    text(board, "OSHW - github.com/Brillar0101", 88.0, 107.3, 1.0, F, 0.16,
         justify="left")
    text(board, "BOOT", 30.0, 29.6, 1.0, F, 0.16)
    text(board, "RST", 40.0, 29.6, 1.0, F, 0.16)
    text(board, "PTT TOUCH", 38.0, 9.4, 1.0, F, 0.16)
    text(board, "MIC", 56.0, 11.8, 1.0, F, 0.16)
    text(board, "SPK", 144.0, 73.6, 1.0, F, 0.16)
    text(board, "3V3 TX GND RX", 6.5, 85.5, 1.0, F, 0.16, angle=0)
    text(board, "BAT+", 140.0, 21.5, 1.0, F, 0.16, justify="right")
    text(board, "GND", 140.0, 25.5, 1.0, F, 0.16, justify="right")
    text(board, "PWR", 146.5, 51.5, 1.0, F, 0.16)
    text(board, "USB-C", 75.0, 10.2, 1.0, F, 0.16)
    # pinout legend on the back (inside the battery pocket zone - flat area)
    legend = ["ClaudeMicroV4  ESP32-S3-WROOM-1",
              "ROW0-3=IO4-7   COL0-5=IO10-15",
              "SDA=IO8 SCL=IO9  LED=IO21  TOUCH=IO1",
              "LCD SCK/MOSI/DC=IO16/17/18  VBAT=IO2",
              "ENC1=IO40-42  ENC2=IO35-37  UART=IO43/44",
              "I2S BCLK/WS=IO38/39 OUT/IN=IO47/48"]
    for i, line in enumerate(legend):
        text(board, line, 119.0, 7.0 + 3.2 * i, 1.2, B, 0.2, mirror=True)
    text(board, "BATTERY 803040 1000mAh POCKET - KEEP CLEAR", 119.0, 28.5, 1.2,
         pcbnew.Dwgs_User, 0.2)


def main():
    comps, nets = parse_netlist(NET)
    board = pcbnew.CreateEmptyBoard()
    board.SetFileName(BRD)
    bds = board.GetDesignSettings()
    bds.SetCopperLayerCount(2)
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
        fix_models(fp, fpid)
        if ref == "J1":
            # V1 fp models its two locating pegs as PLATED holes with zero
            # annulus -> annular_width DRC error; they are pegs, make NPTH
            for pad in fp.Pads():
                if not pad.GetNumber() and pad.HasHole():
                    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
                    pad.SetLayerSet(pad.UnplatedHoleMask())
        if ref not in layout:
            print("NO LAYOUT:", ref)
        x, y, deg, back = layout.get(ref, (75.0, 55.0, 0, False))
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

    # CC2 pad exit (J1-B5) violates freerouting's own clearance vs the wide
    # custom VBUS pad next door - pre-route it here; export_dsn excludes CC2.
    def fixed_track(net, x1, y1, x2, y2, layer, w=0.2):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
        t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetLocked(True)
        board.Add(t)

    cc2 = board.FindNet("CC2")
    b5 = next(p for p in placed["J1"].Pads() if p.GetNumber() == "B5")
    r2 = next(p for p in placed["R2"].Pads() if p.GetNumber() == "1")
    bx, by = b5.GetPosition().x, b5.GetPosition().y
    rx, ry = r2.GetPosition().x, r2.GetPosition().y
    wy = mm(9.05)
    for (x1, y1), (x2, y2) in zip([(bx, by), (bx, wy), (rx, wy), (rx, ry)],
                                  [(bx, wy), (rx, wy), (rx, ry), (rx, ry)]):
        if (x1, y1) != (x2, y2):
            fixed_track(cc2, x1, y1, x2, y2, pcbnew.F_Cu)

    # CC1: R1 sits west of the USB escape fan; freerouting cannot thread the
    # 0.5mm pad row either, so pre-route on B.Cu under the connector.
    cc1 = board.FindNet("CC1")
    a5 = next(p for p in placed["J1"].Pads() if p.GetNumber() == "A5")
    r1 = next(p for p in placed["R1"].Pads() if p.GetNumber() == "1")
    ax, ay = a5.GetPosition().x, a5.GetPosition().y
    r1x, r1y = r1.GetPosition().x, r1.GetPosition().y
    cy = mm(8.7)
    fixed_track(cc1, ax, ay, ax, cy, pcbnew.F_Cu)
    fixed_track(cc1, ax, cy, r1x, cy, pcbnew.B_Cu)
    fixed_track(cc1, r1x, cy, r1x, r1y, pcbnew.F_Cu)
    for vx, vy in ((ax, cy), (r1x, cy)):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(vx), int(vy)))
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(cc1)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetLocked(True)
        board.Add(v)

    # VBUS bridge between the connector's two VBUS pads (B4A9/A4B9): their
    # escapes are boxed in by the 0.5mm pad row, so freerouting reliably
    # abandons one of them - bridge on B.Cu under the connector, locked.
    vbus = board.FindNet("VBUS")
    pj = {p.GetNumber(): p.GetPosition() for p in placed["J1"].Pads()}
    lx, ly = pj["B4A9"].x, pj["B4A9"].y
    rx2, ry2 = pj["A4B9"].x, pj["A4B9"].y
    by2 = mm(7.9)
    fixed_track(vbus, lx, ly, lx, by2, pcbnew.F_Cu, 0.3)
    fixed_track(vbus, lx, by2, rx2, by2, pcbnew.B_Cu, 0.5)
    fixed_track(vbus, rx2, by2, rx2, ry2, pcbnew.F_Cu, 0.3)
    for vx, vy in ((lx, by2), (rx2, by2)):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(vx), int(vy)))
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(vbus)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetLocked(True)
        board.Add(v)

    mounting_holes(board)

    # battery pocket: drawing + no components on the bottom side
    x1, y1, x2, y2 = BATT
    rect(board, x1, y1, x2, y2, pcbnew.Dwgs_User)
    rule_area(board, x1, y1, x2, y2, [pcbnew.B_Cu], no_pour=False,
              no_vias=False, no_footprints=True, name="battery_pocket")
    # antenna sliver: no copper/pour/vias (module antenna overhangs the edge)
    rule_area(board, *ANT_KEEPOUT, [pcbnew.F_Cu, pcbnew.B_Cu], no_pour=True,
              no_vias=True, name="antenna_keepout")
    # touch pad: no ground pour under the pad (DESIGN-V3 rule 6)
    rule_area(board, *TOUCH_VOID, [pcbnew.F_Cu, pcbnew.B_Cu], no_pour=True,
              no_vias=True, name="touch_void")
    # mic acoustic port: no pour/vias over the port hole (DESIGN-V4 rule 11)
    rule_area(board, *MIC_PORT_VOID, [pcbnew.F_Cu, pcbnew.B_Cu], no_pour=True,
              no_vias=True, name="mic_port_void")
    # marker area (no restrictions) naming the USB-C fine-pitch land so the
    # .kicad_dru rule can relax pad-to-pad clearance inside the connector
    rule_area(board, 69.5, 5.9, 80.5, 7.6, [pcbnew.F_Cu], no_pour=False,
              no_tracks=False, no_vias=False, no_footprints=False,
              name="usb_area")

    add_silk(board)
    board.BuildListOfNets()
    pcbnew.SaveBoard(BRD, board)

    # courtyard overlap self-check (same-side bounding boxes)
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
    # audio placement sanity (rules 11/12/14): mic-to-speaker distance and
    # amp-to-speaker-connector distance
    import math
    mk = placed["MK1"].GetPosition()
    j4 = placed["J4"].GetPosition()
    u6 = placed["U6"].GetPosition()
    d_mic_spk = math.hypot(mk.x - j4.x, mk.y - j4.y) / 1e6
    d_amp_j4 = math.hypot(u6.x - j4.x, u6.y - j4.y) / 1e6
    print(f"audio: mic-J4 {d_mic_spk:.1f}mm (>=10 req), U6-J4 {d_amp_j4:.1f}mm"
          f" (<=15 req)")
    # J4 wire-exit direction check: signal pads must sit west of the centre
    px = [p.GetPosition().x for p in placed["J4"].Pads()
          if p.GetNumber() in ("1", "2")]
    print(f"J4 exit: signal pads at x={[round(x/1e6,2) for x in px]} "
          f"(centre 144.0; pads west => wire exits east)")
    print(f"placed {len(placed)} footprints, {made} nets, "
          f"{n_overlap} courtyard overlaps -> {BRD}")


main()

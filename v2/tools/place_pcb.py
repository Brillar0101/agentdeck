#!/usr/bin/env python3
"""Populate v2/hardware/AgentDeckV2.kicad_pcb from the netlist and place parts.

Ported from NeuralCard place_pcb.py. Run with KiCad's bundled python (pcbnew):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/\
Current/bin/python3 v2/tools/place_pcb.py

Board: 150x110 mm, rounded corners r=6, y down, origin top-left.
  - key grid 4 rows x 6 cols, 18 mm pitch: cols x=30..120, rows y=40..94
  - top strip (y<31): ESP32-S3 top-left (antenna overhangs the top edge,
    DESIGN-V2 rule 1), touch pad, USB-C top edge centre, OLED centre,
    EC11 right, power cluster top-right, battery pocket keepout 42x32
  - LEDs reverse-mount on B.Cu at key centre +(0,-4.8) (V1 pattern), matrix
    diode B.Cu at key +(0,+6.5), per-LED 100nF B.Cu at key +(-4.6,-4.8)
"""
import os
import re

import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))          # repo root
HW = os.path.join(ROOT, "v2", "hardware")
NET = os.path.join(HW, "AgentDeckV2.net")
BRD = os.path.join(HW, "AgentDeckV2.kicad_pcb")
V1_SHAPES = os.path.join(ROOT, "v1", "hardware", "JLC.3dshapes")
NC_SHAPES = "/Users/barakaeli/Open Source Hardware/NeuralCard/hardware/JLC.3dshapes"
FPD = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LIB = {
    "V2": os.path.join(HW, "V2.pretty"),
    "JLC_V1": os.path.join(ROOT, "v1", "hardware", "JLC.pretty"),
    "AgentDeck": os.path.join(ROOT, "v1", "hardware", "AgentDeck.pretty"),
    "Diode_SMD": f"{FPD}/Diode_SMD.pretty",
    "Connector_JST": f"{FPD}/Connector_JST.pretty",
    "Package_TO_SOT_SMD": f"{FPD}/Package_TO_SOT_SMD.pretty",
    "Resistor_SMD": f"{FPD}/Resistor_SMD.pretty",
    "Capacitor_SMD": f"{FPD}/Capacitor_SMD.pretty",
}

W, H, R = 150.0, 110.0, 6.0
COLS = [30.0 + 18.0 * c for c in range(5)]
ROWS = [40.0 + 18.0 * r for r in range(4)]
HOLES = [(6, 6), (144, 6), (6, 104), (144, 104), (6, 55), (144, 55)]
BATT = (108.0, 12.0, 142.0, 62.0)      # 34x50 pocket (103450 2000mAh), bottom side keep clear
ANT_KEEPOUT = (10.0, 0.0, 30.0, 0.9)   # copper/pour void under antenna sliver

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
    "OLED1": (67.0, 28.6, 180, False),  # JLC module: body extends +Y, so 180 keeps it above the keys
    "R12": (56.0, 31.0, 0, False),      # SDA pullup
    "R13": (59.5, 31.0, 0, False),      # SCL pullup
    "C10": (63.0, 31.0, 0, False),      # OLED 100nF
    "ENC1": (90.0, 16.0, 0, False),
    "JS1": (126.0, 84.0, 0, False),     # Alps 5-way joystick, right strip under the pocket
    "SW26": (34.0, 25.5, 0, False),     # BOOT
    "SW27": (44.0, 25.5, 0, False),     # RESET
    # module decoupling + EN/IO0 networks on B.Cu under the module, next to
    # the pins they serve (3V3 = pin 2, EN = pin 3, both top of the left
    # column; IO0 = pin 27, bottom of the right column). Keeps the front
    # strip below the module free for the 9 bottom-row pin escapes.
    "C1": (13.5, 4.0, 90, True),        # 100nF, at pin 2 (3V3)
    "C2": (13.5, 8.0, 90, True),
    "C3": (13.5, 12.0, 90, True),
    "C4": (17.0, 6.0, 90, True),        # 10uF bulk
    "R9": (17.0, 10.5, 90, True),       # EN pullup, near pin 3
    "C5": (17.0, 14.5, 90, True),       # EN 100nF
    "R10": (25.5, 14.0, 90, True),      # IO0 pullup, near pin 27
    "J3": (6.5, 40.0, 90, False),       # UART prog pads, left edge
    # LED chain head (B.Cu, next to LED1 under SW1)
    "U2": (24.0, 31.0, 0, True),
    "C9": (20.0, 34.0, 90, True),
    "R11": (27.8, 30.0, 0, True),
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
    "R4": (116.5, 16.5, 0, False),      # CHRG 10k
    "R5": (121.5, 16.5, 0, False),      # STDBY 10k
    "R7": (127.0, 17.0, 0, False),      # VBAT div 100k
    "R8": (132.0, 17.0, 0, False),      # VBAT div 47k
    "C8": (137.0, 17.0, 0, False),
    "J2": (143.5, 25.0, 180, False),    # JST-PH battery, wire exits toward pocket
    "SW25": (147.6, 45.0, 90, False),   # power switch, actuator over right edge
}

# keys, diodes, LEDs (serpentine chain), per-LED caps.
# Choc pins sit at (0,-5.9)/(5,-3.8) = north side; the switch LED slot (and so
# the reverse-mount SK6812) goes on the opposite side at +4.8 (V1 convention:
# LED opposite the pins). Matrix diode tucks NW, clear of pin 1 and the posts.
for idx in range(20):
    r, c = idx // 5, idx % 5
    kx, ky = COLS[c], ROWS[r]
    layout[f"SW{idx + 1}"] = (kx, ky, 0, False)
    layout[f"D{idx + 1}"] = (kx - 5.0, ky - 6.0, 0, True)
    led_i = r * 5 + (c if r % 2 == 0 else 4 - c)      # serpentine LED order
    layout[f"LED{led_i + 1}"] = (kx, ky + 4.8, 180 if r % 2 else 0, True)
    layout[f"C{12 + led_i}"] = (kx - 4.6, ky + 4.8, 90, True)


sys.path.insert(0, HERE)
from attach_3d import STEP as JLC_STEP  # noqa: E402


def fix_models(fp, fpid):
    """Rewrite 3D model paths that are only valid in their home projects.
    Mutating FP_3DMODEL elements in place does not stick through SWIG -
    rebuild the model list (same trick as V1 add_switch_bodies.py)."""
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
        # JLCPCB/EasyEDA STEP models (v2/hardware/jlc3d, see tools/attach_3d.py)
        fpname = fpid.split(":")[-1]
        if fpname in JLC_STEP:
            fn = "${KIPRJMOD}/jlc3d/JLC.3dshapes/" + JLC_STEP[fpname]
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
    # Kept to what a person needs while holding the board. GPIO legend and
    # flashing recipe live in firmware/AgentDeckV2/pins.h and the README.
    text(board, "AgentDeck V2", 24.0, 106.3, 1.6, F, 0.3, justify="left")
    text(board, "BOOT", 34.0, 29.6, 1.0, F, 0.16)
    text(board, "RST", 44.0, 29.6, 1.0, F, 0.16)
    text(board, "3V3 TX GND RX", 6.5, 47.5, 1.0, F, 0.16, angle=0)
    text(board, "BAT+", 140.0, 21.5, 1.0, F, 0.16, justify="right")
    text(board, "GND", 140.0, 25.5, 1.0, F, 0.16, justify="right")
    text(board, "PWR", 146.5, 51.5, 1.0, F, 0.16)
    text(board, "github.com/Brillar0101/agentdeck", 125.0, 100.0, 1.2, B, 0.2,
         mirror=True)
    text(board, "103450 POCKET", 125.0, 45.0, 1.2, pcbnew.Dwgs_User, 0.2)


# ---- pre-routes: nets freerouting could not close on V2 (runs 1-3) ---------
# USB pair: ESP left-column pins 13/14 -> B.Cu lanes y=16.25/17.52 -> J1 with the
# A/B pad jogs (DP north jog, DM south jog: the only non-crossing pairing of the
# interleaved B6 A7 A6 B7 pads) -> USBLC6 U3. +3V3: pin 2 -> module decoupling
# cluster on B.Cu -> top-edge spine y=2.28 -> x=60 -> y=19.5 spine -> LDO U5,
# with branches to OLED1/R12/R13/C10 and the J3 prog pad. All locked; export_dsn
# fences them and finish_v2.del_box skips locked copper.
F_, B_ = pcbnew.F_Cu, pcbnew.B_Cu
PREROUTES = [
    ("USB_DM", 0.2, [
        [(11.25, 16.25, F_), (9.6, 16.25, F_), (9.6, 16.25, B_), (80.6, 16.25, B_),
         (80.6, 6.45, B_), (80.6, 6.45, F_), (82.55, 6.45, F_), (82.55, 4.15, F_)],
        [(74.75, 16.25, B_), (74.75, 10.3, B_), (74.75, 10.3, F_), (74.75, 6.87, F_)],
        [(74.75, 7.9, F_), (75.75, 7.9, F_), (75.75, 6.87, F_)],
    ]),
    ("USB_DP", 0.2, [
        [(11.25, 17.52, F_), (9.6, 17.52, F_), (9.6, 17.52, B_), (81.6, 17.52, B_),
         (81.6, 3.22, B_), (81.6, 3.22, F_), (75.25, 3.22, F_), (75.25, 6.87, F_)],
        [(75.25, 5.6, F_), (74.25, 5.6, F_), (74.25, 6.87, F_)],
        [(81.6, 3.22, F_), (84.45, 3.22, F_), (84.45, 4.15, F_), (84.45, 6.45, F_)],
    ]),
    # +3V3: only the module decoupling comb is fixed (pin 2 -> via -> C1..C4,
    # R9.1). The long distribution is left to the router (In2 is free).
    ("+3V3", 0.25, [
        [(11.25, 2.28, F_), (9.6, 2.28, F_), (9.6, 2.28, B_), (9.6, 4.775, B_),
         (13.5, 4.775, B_), (14.6, 4.775, B_), (14.6, 12.775, B_), (13.5, 12.775, B_)],
        [(14.6, 8.775, B_), (13.5, 8.775, B_)],
        [(14.6, 6.95, B_), (17.0, 6.95, B_)],
        [(14.6, 11.325, B_), (17.0, 11.325, B_)],
    ]),
]


def preroute(board, placed, fixed_track):
    n_t = n_v = 0
    for net_name, w, paths in PREROUTES:
        net = board.FindNet(net_name)
        if net is None:
            raise SystemExit(f"preroute: no net {net_name}")
        for pts in paths:
            for (x1, y1, l1), (x2, y2, l2) in zip(pts, pts[1:]):
                if l1 != l2:
                    assert (x1, y1) == (x2, y2), f"{net_name}: via must not move"
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(V(x1, y1))
                    v.SetWidth(mm(0.6))
                    v.SetDrill(mm(0.3))
                    v.SetNet(net)
                    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    v.SetLocked(True)
                    board.Add(v)
                    n_v += 1
                else:
                    fixed_track(net, mm(x1), mm(y1), mm(x2), mm(y2), l1, w)
                    n_t += 1
    print(f"preroute: {n_t} locked tracks, {n_v} locked vias")


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

    preroute(board, placed, fixed_track)

    mounting_holes(board)

    # battery pocket: drawing + no components on the bottom side
    x1, y1, x2, y2 = BATT
    rect(board, x1, y1, x2, y2, pcbnew.Dwgs_User)
    rule_area(board, x1, y1, x2, y2, [pcbnew.B_Cu], no_pour=False,
              no_vias=False, no_footprints=True, name="battery_pocket")
    # antenna sliver: no copper/pour/vias (module antenna overhangs the edge)
    rule_area(board, *ANT_KEEPOUT, [pcbnew.F_Cu, pcbnew.B_Cu], no_pour=True,
              no_vias=True, name="antenna_keepout")
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
    print(f"placed {len(placed)} footprints, {made} nets, "
          f"{n_overlap} courtyard overlaps -> {BRD}")


main()

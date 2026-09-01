#!/usr/bin/env python3
"""Point every footprint's 3D model at the JLCPCB/EasyEDA STEP files in
v2/hardware/jlc3d/JLC.3dshapes (downloaded with easyeda2kicad --3d per LCSC
code). Edits the board in place - close KiCad first, reopen after.

Run with KiCad python:  .../python3 v2/tools/attach_3d.py [board.kicad_pcb]
Offsets/rotations are left at the footprint's existing values; check the
3D viewer once - EasyEDA models occasionally need a 90/180 degree turn.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
B = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HW, "AgentDeckV2.kicad_pcb")
D = "${KIPRJMOD}/jlc3d/JLC.3dshapes/"

# footprint name (after the lib prefix) -> STEP file
STEP = {
    "WIRELM-SMD_ESP32-S3-WROOM-1": "WIRELM-SMD_ESP32-S3-WROOM-1.step",
    "ESOP-8_TP4056": "ESOP-8_L4.9-W3.9-H1.6-LS6.0-P1.27.step",
    "MSK12C02": "SW-SMD_3P-L6.6-W2.7-LS7.8-P1.50.step",
    "ChocV1_Direct": "KEY-TH_CPG135001D0X.step",
    "LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E": "LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E.step",
    "SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR": "SOT-23-5_L2.9-W1.6-H1.1-LS2.8-P0.95.step",
    "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL": "SOT-23-6_L2.9-W1.6-H1.5-LS2.8-P0.95.step",
    "SOT-23": "SOT-23-3P_L2.9-W1.3-H1.0-LS2.4-P0.95.step",
    "USB-C_SMD-TYPE-C-31-M-12_1": "USB-C_SMD-TYPE-C-31-M-12_1.step",
    "SW-TH_EC11E1820402": "SW-TH_EC11E1820402-L11.7-W12.0-H24.5-P2.5-LS14.5.step",
    "SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5": "SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5.step",
    "SW-SMD_SKRHABE010": "SW-SMD_SKRHABE010.step",
    "D_SOD-123": "SOD-123F_L2.7-W1.6-LS3.8-RD.step",
    "D_SMA": "SMA_L4.3-W2.6-LS5.2-RD.step",
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": "CONN-SMD_P2.00_S2B-PH-SM4-TB-LF-SN.step",
    "R_0603_1608Metric": "R0603.step",
    "C_0603_1608Metric": "C0603_L1.6-W0.8-H0.8.step",
    "C_0805_2012Metric": "C0805_L2.0-W1.3-H1.3.step",
}


def main():
    b = pcbnew.LoadBoard(B)
    n = 0
    for fp in b.GetFootprints():
        name = fp.GetFPID().GetLibItemName().wx_str()
        step = STEP.get(name)
        if not step:
            continue
        models = [(m.m_Offset, m.m_Rotation, m.m_Scale) for m in fp.Models()] or \
            [(pcbnew.VECTOR3D(0, 0, 0), pcbnew.VECTOR3D(0, 0, 0), pcbnew.VECTOR3D(1, 1, 1))]
        fp.Models().clear()
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = D + step
        m.m_Offset, m.m_Rotation, m.m_Scale = models[0]
        fp.Models().push_back(m)
        n += 1
    pcbnew.SaveBoard(B, b)
    print(f"attach_3d: {n} footprints now reference jlc3d STEP models -> {B}")


if __name__ == "__main__":
    main()

"""Case revision: 4 M2.5 corner mounting holes + keepouts, relocate intruders.

Corners are rounded r=6mm, so holes sit at the arc centers (6,6),(84,6),
(6,84),(84,84) where board material is thickest. Each hole gets a circular
rule-area keepout (no tracks/vias/pads/copper) so the reroute avoids it.
C16 (bypass cap) and SW13 (BOOT button) are nudged out of the bottom keepouts.
"""
import math

import pcbnew

B = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
mm = pcbnew.FromMM
HOLES = [(6.0, 6.0), (84.0, 6.0), (6.0, 84.0), (84.0, 84.0)]
DRILL = 2.7          # M2.5 clearance hole
KEEPOUT_R = 3.4      # no-copper radius around each hole

board = pcbnew.LoadBoard(B)
d = {f.GetReference(): f for f in board.GetFootprints()}

# 1. relocate intruders out of the bottom keepouts
d["C16"].SetPosition(pcbnew.VECTOR2I(mm(10.5), mm(79.5)))
d["SW13"].SetPosition(pcbnew.VECTOR2I(mm(75.0), mm(80.5)))
print("moved C16 -> (10.5,79.5), SW13/BOOT -> (75.0,80.5)")

# 2. remove any prior mounting holes / keepouts (idempotent)
for fp in list(board.GetFootprints()):
    if fp.GetReference().startswith("MH"):
        board.Remove(fp)
for z in list(board.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName().startswith("mh_keepout"):
        board.Remove(z)

# 3. add mounting holes as footprints with a single NPTH pad
for i, (x, y) in enumerate(HOLES, 1):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(f"MH{i}")
    fp.SetValue("M2.5")
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mm(DRILL), mm(DRILL)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(DRILL), mm(DRILL)))
    pad.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    pad.SetLayerSet(pad.UnplatedHoleMask())
    fp.Add(pad)
    board.Add(fp)

# 4. circular keepouts (16-gon) around each hole
for i, (x, y) in enumerate(HOLES, 1):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(f"mh_keepout{i}")
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowFootprints(False)
    z.SetLayerSet(pcbnew.LSET.AllCuMask(2))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for k in range(16):
        a = 2 * math.pi * k / 16
        ch.Append(mm(x + KEEPOUT_R * math.cos(a)), mm(y + KEEPOUT_R * math.sin(a)))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    board.Add(z)

pcbnew.SaveBoard(B, board)
print(f"added {len(HOLES)} M2.5 mounting holes + keepouts")
print("DSN:", pcbnew.ExportSpecctraDSN(board, B.replace(".kicad_pcb", ".dsn")))

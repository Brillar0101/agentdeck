"""Replace malformed courtyards (easyeda2kicad imports) with clean bounding rectangles."""
import pcbnew

BOARD = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
BAD = {"SW%d" % i for i in range(1, 13)} | {"U1"}

board = pcbnew.LoadBoard(BOARD)
M = pcbnew.FromMM(0.25)

# Phase 1: gather geometry (no mutation — mutating breaks SWIG dispatch on later iteration)
plans = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref not in BAD:
        continue
    cy_layer = pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
    xs, ys = [], []
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        xs += [bb.GetLeft(), bb.GetRight()]
        ys += [bb.GetTop(), bb.GetBottom()]
    to_remove = []
    for item in fp.GraphicalItems():
        if item.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            to_remove.append(item)
        elif isinstance(item, pcbnew.PCB_SHAPE):
            bb = item.GetBoundingBox()
            xs += [bb.GetLeft(), bb.GetRight()]
            ys += [bb.GetTop(), bb.GetBottom()]
    plans.append((fp, ref, cy_layer, min(xs) - M, max(xs) + M, min(ys) - M, max(ys) + M, to_remove))

# Phase 2: mutate
for fp, ref, cy_layer, x0, x1, y0, y1, to_remove in plans:
    for item in to_remove:
        fp.Remove(item)
    rect = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECTANGLE)
    rect.SetStart(pcbnew.VECTOR2I(x0, y0))
    rect.SetEnd(pcbnew.VECTOR2I(x1, y1))
    rect.SetLayer(cy_layer)
    rect.SetWidth(pcbnew.FromMM(0.05))
    rect.SetFilled(False)
    fp.Add(rect)
    print(f"{ref}: courtyard {pcbnew.ToMM(x1 - x0):.1f}x{pcbnew.ToMM(y1 - y0):.1f}mm "
          f"on {'F' if cy_layer == pcbnew.F_CrtYd else 'B'}.CrtYd")

pcbnew.SaveBoard(BOARD, board)
print("board saved")

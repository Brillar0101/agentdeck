"""Place Choc switch 3D bodies on the TOP face via dedicated carrier footprints.

The hot-swap sockets live on B.Cu, so a model attached to them renders on the
bottom. KiCad ties a model's board side to its footprint, so we add a padless
carrier footprint on F.Cu at each key center to hold the switch (and keycap)
body on the user-facing side. Carriers are excluded from BOM and position files.
"""
import pcbnew

B = "/Users/barakaeli/kicad-projects/claude-micro/hardware/ClaudeMicro.kicad_pcb"
mm = pcbnew.FromMM
KEY_REFS = {f"SW{i}" for i in range(1, 13)} | {"SW14"}
# switch centre (pole/keycap) = socket footprint origin + this board-space offset
# (these hotswap sockets are on B.Cu; measured uniform across all 12, rot 0)
CENTER_DX, CENTER_DY = mm(2.5), mm(-4.8)

board = pcbnew.LoadBoard(B)

# 1. strip switch/keycap models off the sockets and collect key centers
centers = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref in KEY_REFS:
        p = fp.GetPosition()
        centers.append((ref, p.x + CENTER_DX, p.y + CENTER_DY, fp.GetOrientationDegrees()))
        keep = [(m.m_Filename, m.m_Offset, m.m_Rotation, m.m_Scale)
                for m in fp.Models()
                if "ChocV1" not in m.m_Filename and "Keycap" not in m.m_Filename]
        fp.Models().clear()
        for fn, off, rot, sc in keep:
            m = pcbnew.FP_3DMODEL()
            m.m_Filename, m.m_Offset, m.m_Rotation, m.m_Scale = fn, off, rot, sc
            fp.Models().push_back(m)

# 2. remove any prior carriers (idempotent re-run)
for fp in list(board.GetFootprints()):
    if fp.GetReference().startswith("KEY"):
        board.Remove(fp)

# 3. add a carrier per key on F.Cu
s = 1 / 2.54
for ref, x, y, rot in centers:
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("KEY" + ref[2:])
    fp.SetValue("ChocSwitch")
    fp.SetPosition(pcbnew.VECTOR2I(x, y))
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)

    # keycap outline box on Dwgs.User (documentation layer): shows where the cap
    # sits, visible in the PCB editor but NOT on the manufactured board.
    half_w = mm(1.75 * 17.5 / 2) if ref == "SW11" else mm(17.5 / 2)  # SW11 = 1.75u
    half_h = mm(17.5 / 2)
    box = pcbnew.PCB_SHAPE(fp)
    box.SetShape(pcbnew.SHAPE_T_RECT)
    box.SetStart(pcbnew.VECTOR2I(x - half_w, y - half_h))
    box.SetEnd(pcbnew.VECTOR2I(x + half_w, y + half_h))
    box.SetLayer(pcbnew.Dwgs_User)
    box.SetWidth(mm(0.15))
    box.SetFilled(False)
    fp.Add(box)

    ADD_BODIES = False  # user places physical switches themselves; carriers keep only the outline boxes
    if ADD_BODIES:
        body = pcbnew.FP_3DMODEL()
        body.m_Filename = "${KIPRJMOD}/JLC.3dshapes/ChocV1.wrl"
        body.m_Offset = pcbnew.VECTOR3D(0.0, 0.0, 3.0)  # model extends 3mm below origin
        body.m_Rotation = pcbnew.VECTOR3D(0.0, 0.0, 0.0)
        body.m_Scale = pcbnew.VECTOR3D(1.0, 1.0, 1.0)
        fp.Models().push_back(body)

    ADD_CAPS = False   # user: no caps yet; KEY11 gets 1.75x wide cap (spacebar) when enabled
    if not ADD_CAPS:
        board.Add(fp)
        continue
    cap = pcbnew.FP_3DMODEL()
    cap.m_Filename = "${KIPRJMOD}/JLC.3dshapes/ChocKeycap.x3d"
    cap.m_Offset = pcbnew.VECTOR3D(0.0, 0.0, 6.0)
    cap.m_Rotation = pcbnew.VECTOR3D(0.0, 0.0, 0.0)
    wide = 1.75 if ref == 'SW11' else 1.0
    cap.m_Scale = pcbnew.VECTOR3D(s * wide, s, s)
    fp.Models().push_back(cap)

    board.Add(fp)

pcbnew.SaveBoard(B, board)
print(f"placed {len(centers)} switch carriers on F.Cu")

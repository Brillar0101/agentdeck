"""Parametric generator for the AgentDeck V2 enclosure.

Run with Blender:
    blender -b --python v2/enclosure/src/generate_case.py -- <output-dir>

V2 differs from V1 structurally: components sit on the TOP of the board
(only the hot-swap sockets, LEDs, diodes and their caps hang below), so the
lid is not a flat plate but a shell with an internal cavity that clears the
ESP32 module and USB shell, with clamp bosses reaching down to the board at
the screw points. The tray below is shallow - just socket depth.

All coordinates are PCB millimetres, matching v2/hardware/AgentDeckV2.kicad_pcb.
Blender space is x -> x/1000, y -> -y/1000, z -> z/1000.
"""
import math
import sys

import bpy
import bmesh

# ---------------------------------------------------------------- parameters
BOARD_MIN, BOARD_MAX = 0.0, 112.0      # 112 x 112 board outline
BOARD_R = 6.0
ARC = (6.0, 106.0)                     # corner-arc centres, both axes
WALL = 2.6
CASE_R = BOARD_R + WALL

# z: PCB spans 0..1.6 (top face at 1.6)
LID_Z = (1.6, 8.4)                     # shell over the component side
LID_CAVITY_TOP = 5.2                   # inner cavity roof: ESP32 shield 3.2 + margin
TRAY_Z = (-4.4, 1.6)                   # shallow: sockets are 3.05 mm
FLOOR = 1.2
FIT = 0.40

SCREWS = [(6.0, 6.0), (106.0, 6.0), (6.0, 106.0), (106.0, 106.0)]

# Fastener stack identical to V1 (proven):
#   cover cap -> counterbore -> M2.5x8 button head -> lid boss -> PCB -> insert
SCREW = "M2.5 x 8 button head, ISO 7380"
HEAD_D, HEAD_H = 4.70, 1.30
COVER_D, COVER_H = 5.00, 1.20
CBORE_D = 5.20
CBORE_DEPTH = HEAD_H + COVER_H         # 2.50
SHAFT_D = 2.90
INSERT = "M2.5 x 5.0 mm brass heat-set, 4.0 mm OD"
INSERT_D, INSERT_L = 3.60, 5.00
BOSS_D = 8.00

# key grid: 4 rows x 5 cols, 18.7 x 19.3 pitch (from place_pcb.py)
COLS = [18.6 + 18.7 * c for c in range(5)]
ROWS = [42.0 + 19.3 * r for r in range(4)]
KEY_W = 17.65                          # same cap clearance as V1
KEYS = [(cx - KEY_W / 2, cx + KEY_W / 2, cy - KEY_W / 2, cy + KEY_W / 2)
        for cy in ROWS for cx in COLS]

ENC = (31.35, 46.65, 4.8, 21.2)        # EC11 at (39,13): V1-sized opening
JOY = (79.9, 92.1, 7.45, 18.55)        # SKQUCAA010 at (86,13)
BOOTHOLES = [(32.0, 28.0), (41.0, 28.0)]   # BOOT / RST pinholes through the lid
BOOT_D = 2.0

# USB-C: J1 at x=60, mouth over the top edge (y=0), shell on the TOP face,
# z 1.6..4.86. Port through the lid's front wall; cut after the bevel.
USB_X = (55.2, 64.8)                   # shell 8.94 + margin
USB_Z = (1.45, 5.0)
NOTCH_X = (54.3, 65.7)                 # slim overmould collar
NOTCH_Z = (0.9, 5.7)

OUT = sys.argv[-1]
scratch = []


def P(x, y, z):
    return (x / 1000.0, -y / 1000.0, z / 1000.0)


def rrect_pts(r, seg=32):
    a0, a1 = ARC
    out = []
    for cx, cy, s in ((a1, a0, -90.0), (a1, a1, 0.0), (a0, a1, 90.0), (a0, a0, 180.0)):
        for i in range(seg + 1):
            a = math.radians(s + 90.0 * i / seg)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def prism(name, pts, z0, z1):
    bm = bmesh.new()
    ring = [bm.verts.new(P(x, y, z0)) for x, y in pts]
    bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    r = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    verts = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, (z1 - z0) / 1000.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def box(name, x0, x1, y0, y1, z0, z1):
    return prism(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def cylinder(name, cx, cy, d, z0, z1, seg=48):
    pts = [(cx + d / 2 * math.cos(2 * math.pi * i / seg),
            cy + d / 2 * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    return prism(name, pts, z0, z1)


def cut(target, tool):
    bpy.context.view_layer.objects.active = target
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation, m.object, m.solver = 'DIFFERENCE', tool, 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m.name)
    scratch.append(tool)


def add(target, tool):
    bpy.context.view_layer.objects.active = target
    m = target.modifiers.new("u", 'BOOLEAN')
    m.operation, m.object, m.solver = 'UNION', tool, 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m.name)
    scratch.append(tool)


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- top shell
lid = prism("CaseTop", rrect_pts(CASE_R), *LID_Z)
lo, hi = LID_Z
# internal cavity over the component field (walls stay solid)
cut(lid, prism("cavity", rrect_pts(BOARD_R + FIT), lo, LID_CAVITY_TOP))
# clamp bosses back down to the board at the screws
for i, (cx, cy) in enumerate(SCREWS):
    add(lid, cylinder("lboss%d" % i, cx, cy, BOSS_D, lo, LID_CAVITY_TOP))
for i, (x0, x1, y0, y1) in enumerate(KEYS):
    cut(lid, box("k%d" % i, x0, x1, y0, y1, lo - 1, hi + 1))
cut(lid, box("enc", *ENC, lo - 1, hi + 1))
cut(lid, box("joy", *JOY, lo - 1, hi + 1))
for i, (cx, cy) in enumerate(BOOTHOLES):
    cut(lid, cylinder("bh%d" % i, cx, cy, BOOT_D, lo - 1, hi + 1))
for i, (cx, cy) in enumerate(SCREWS):
    cut(lid, cylinder("sh%d" % i, cx, cy, SHAFT_D, lo - 1, hi + 1))
    cut(lid, cylinder("cb%d" % i, cx, cy, CBORE_D, hi - CBORE_DEPTH, hi + 1))
print("  screw stack: %s into %s" % (SCREW, INSERT))
print("lid shell: cavity roof z=%.1f, %d keys, encoder, joystick, %d pinholes"
      % (LID_CAVITY_TOP, len(KEYS), len(BOOTHOLES)))

# ---------------------------------------------------------------- bottom tray
tray = prism("CaseBottom", rrect_pts(CASE_R), *TRAY_Z)
tlo, thi = TRAY_Z
cut(tray, prism("pocket", rrect_pts(BOARD_R + FIT), tlo + FLOOR, thi + 1))
BOSS_TOP = 0.0
for i, (cx, cy) in enumerate(SCREWS):
    add(tray, cylinder("boss%d" % i, cx, cy, BOSS_D, tlo + FLOOR, BOSS_TOP))
for i, (cx, cy) in enumerate(SCREWS):
    cut(tray, cylinder("ins%d" % i, cx, cy, INSERT_D, BOSS_TOP - INSERT_L - 0.4, BOSS_TOP + 1))
import bmesh as _bm
_b = _bm.new(); _b.from_mesh(tray.data)
_bm.ops.remove_doubles(_b, verts=_b.verts, dist=1e-6)
_deg = [f for f in _b.faces if f.calc_area() < 1e-10]
if _deg:
    _bm.ops.delete(_b, geom=_deg, context='FACES')
_b.to_mesh(tray.data); _b.free(); tray.data.update()
print("tray: pocket %.1f deep + %d bosses; membranes cleaned: %d"
      % (BOSS_TOP - (tlo + FLOOR), len(SCREWS), len(_deg)))

# ---------------------------------------------------------------- cover cap
capobj = cylinder("CoverCap", 0.0, 0.0, COVER_D, 0.0, COVER_H)

for o in scratch:
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- soften edges
for o in (lid, tray, capobj):
    bpy.context.view_layer.objects.active = o
    bv = o.modifiers.new("soften", 'BEVEL')
    bv.width = 0.0006
    bv.segments = 3
    bv.limit_method = 'ANGLE'
    bv.angle_limit = 0.698
    bpy.ops.object.modifier_apply(modifier=bv.name)
print("edges softened: 0.6mm bevel")

# USB port cut post-bevel (V1 lesson: a bevel chokes small openings).
# The port pierces the LID's front wall - the connector sits on the top face.
cut(lid, box("usbport", USB_X[0], USB_X[1], -CASE_R - 1, 1.2, USB_Z[0], USB_Z[1]))
cut(lid, box("usbnotch", NOTCH_X[0], NOTCH_X[1], -CASE_R - 1, -1.2, NOTCH_Z[0], NOTCH_Z[1]))
print("USB side port cut post-bevel in the lid front wall")

# ---------------------------------------------------------------- report
for o in (lid, tray, capobj):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    d = o.dimensions
    print("%-11s %6.2f x %6.2f x %5.2f mm | %5d faces | non-manifold edges: %d"
          % (o.name, d.x * 1000, d.y * 1000, d.z * 1000, len(o.data.polygons), nm))
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    path = "%s/%s.stl" % (OUT, {lid: "case-top-lid", tray: "case-bottom",
                                 capobj: "case-cover-plug"}[o])
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, global_scale=1000.0)
    else:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True, global_scale=1000.0)

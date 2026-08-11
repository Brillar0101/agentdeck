"""Parametric generator for the AgentDeck enclosure.

Run with Blender:
    blender -b --python enclosure/src/generate_case.py -- <output-dir>

Why this exists
---------------
The enclosure previously had no source - only STLs - and those STLs were not
watertight: CaseTop carried 3324 non-manifold edges, 2373 of them shared by
more than two faces. Blender's EXACT boolean solver requires manifold input, so
every attempt to patch the meshes failed silently (plugs vanished, cuts did not
cut), and the FAST solver crashed outright. Generating clean primitives instead
makes every boolean reliable and every future change a one-line edit.

All coordinates are PCB millimetres, matching hardware/AgentDeck.kicad_pcb.
Blender space is x -> x/1000, y -> -y/1000, z -> z/1000.
"""
import math
import sys

import bpy
import bmesh

# ---------------------------------------------------------------- parameters
BOARD_MIN, BOARD_MAX = -2.5, 92.5      # 95 x 95 board outline
BOARD_R = 6.0                          # board corner radius
ARC = (3.5, 86.5)                      # corner-arc centres, both axes
WALL = 2.6                             # case overhang beyond the board
CASE_R = BOARD_R + WALL                # 8.6 mm outer corner radius

LID_Z = (1.6, 5.5)                     # top plate: sits on the board face
TRAY_Z = (-6.4, 1.6)                   # bottom shell
FLOOR = 1.2                            # tray floor thickness
FIT = 0.40                             # board-to-wall clearance per side (loose FDM drop-in fit)

SCREWS = [(3.086, 3.086), (86.914, 3.086), (3.086, 86.914), (86.914, 86.914)]

# Fastener stack, top to bottom:
#   cover cap  -> counterbore -> screw head -> lid -> PCB -> heat-set insert
#
# The lid is only 3.9 mm thick, so an ISO 4762 socket cap (head 2.5 mm high)
# plus a 1.2 mm cover leaves 0.2 mm of lid under the counterbore - too thin to
# print or to take any clamping load. An ISO 7380 button head is 1.3 mm high
# and leaves 1.4 mm, so the design uses button heads.
SCREW = "M2.5 x 8 button head, ISO 7380"
HEAD_D, HEAD_H = 4.70, 1.30            # ISO 7380 M2.5
COVER_D, COVER_H = 5.00, 1.20          # printed cap, 0.2 mm clearance in the bore
CBORE_D = 5.20                         # head + cover clearance
CBORE_DEPTH = HEAD_H + COVER_H         # 2.50 mm; leaves 1.40 mm of lid
SHAFT_D = 2.90                         # M2.5 free-fit clearance through the lid
INSERT = "M2.5 x 5.0 mm brass heat-set, 4.0 mm OD"
INSERT_D, INSERT_L = 3.60, 5.00        # bore is under the 4.0 OD so it melts in
BOSS_D = 8.00                          # 2.2 mm wall around the insert

KEYS = [                               # exact cutouts read from the PCB
    (26.51, 44.16, 7.17, 24.82), (45.84, 63.49, 7.17, 24.82),
    (7.17, 24.82, 25.84, 43.49), (26.51, 44.16, 25.84, 43.49),
    (45.84, 63.49, 25.84, 43.49), (65.17, 82.83, 25.84, 43.49),
    (7.17, 24.82, 44.51, 62.16), (26.51, 44.16, 44.51, 62.16),
    (45.84, 63.49, 44.51, 62.16), (65.17, 82.83, 44.51, 62.16),
    (7.17, 24.82, 63.18, 80.83), (29.61, 60.39, 63.18, 80.83),
    (65.17, 82.83, 63.18, 80.83),
]
ENC = (7.84, 23.12, 4.83, 21.21)       # rotary encoder
JOY = (67.90, 80.10, 10.47, 21.52)     # 5-way joystick
# USB-C access. J1 stays put (moving it needs a full B.Cu reroute), so the
# opening comes to the connector instead. Sized for the PLUG, not the socket:
# the shell is only 8.34 x 2.56 mm but a typical overmould is ~12 x 6.5 mm and
# a chunky cable is bigger, so a tight slot traps the lead even though the plug
# itself mates. The slot therefore spans the tray wall as well as the lid, and
# gets a flared mouth on the outer face so the cable is guided, not pinched.
# USB-C access, side-port style: the top face stays SOLID over the connector.
# Three cuts replace the old open trench:
#   1. underside pocket - cavity from below over J1's 3.2mm shell, leaving a
#      0.55mm roof (top face unbroken over the board)
#   2. side tunnel - the plug shell's path through the front wall, under the roof
#   3. edge notch - a slim full-height nick at the very rim so the 6.5mm-tall
#      cable overmould (taller than the case - can never come inside) gets
#      2.2mm closer and the plug seats fully (6.0mm insertion, needs ~6)
USB_X = (39.75, 50.25)                 # tunnel: shell 8.94 + 0.78/side
POCKET = (39.50, 50.50, -3.00, 6.60, 4.95)   # x0,x1,y0,y1,ceiling-z
NOTCH = (38.60, 51.40, -5.20, -2.85)   # 12.8 wide for the 12mm overmould
USB_Z_BOTTOM = 0.00                    # down through the tray wall to the PCB
FLARE_X = (36.00, 54.00)               # 18.0 wide lead-in
FLARE_Z = (-1.00, 6.50)
FLARE_DEPTH = 1.60                     # how far the flare reaches inward
LEDS = [(5.5, 62.0), (5.5, 66.5), (5.5, 71.0)]
LED_D = 1.8
BOOT = (75.5, 84.0)                    # BOOTSEL pinhole, so reflashing is possible
BOOT_D = 2.0

OUT = sys.argv[-1]
scratch = []


def P(x, y, z):
    return (x / 1000.0, -y / 1000.0, z / 1000.0)


def rrect_pts(r, seg=32):
    """Outline of a rounded rectangle built on the corner-arc centres."""
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

# ---------------------------------------------------------------- top lid
lid = prism("CaseTop", rrect_pts(CASE_R), *LID_Z)
lo, hi = LID_Z
for i, (x0, x1, y0, y1) in enumerate(KEYS):
    cut(lid, box("k%d" % i, x0, x1, y0, y1, lo - 1, hi + 1))
cut(lid, box("enc", *ENC, lo - 1, hi + 1))
cut(lid, box("joy", *JOY, lo - 1, hi + 1))
# no USB cuts in the lid: J1 hangs BELOW the board (all SMD parts do - the
# sockets/RP2040/USB face down into the tray). The lid front edge is solid.
for i, (cx, cy) in enumerate(LEDS):
    cut(lid, cylinder("led%d" % i, cx, cy, LED_D, lo - 1, hi + 1))
cut(lid, cylinder("boot", *BOOT, BOOT_D, lo - 1, hi + 1))
for i, (cx, cy) in enumerate(SCREWS):
    cut(lid, cylinder("sh%d" % i, cx, cy, SHAFT_D, lo - 1, hi + 1))
    cut(lid, cylinder("cb%d" % i, cx, cy, CBORE_D, hi - CBORE_DEPTH, hi + 1))
print("  screw stack: %s into %s" % (SCREW, INSERT))
print("  counterbore %.2f dia x %.2f deep, shaft %.2f dia, %.2f mm of lid beneath"
      % (CBORE_D, CBORE_DEPTH, SHAFT_D, (hi - lo) - CBORE_DEPTH))
print("lid: %d keys, encoder, joystick, USB, %d LED windows, BOOTSEL, %d screws"
      % (len(KEYS), len(LEDS), len(SCREWS)))

# ---------------------------------------------------------------- bottom tray
tray = prism("CaseBottom", rrect_pts(CASE_R), *TRAY_Z)
tlo, thi = TRAY_Z
cut(tray, prism("pocket", rrect_pts(BOARD_R + FIT), tlo + FLOOR, thi + 1))
BOSS_TOP = 0.0                         # PCB underside - the board sits on these
# side port in the TRAY wall: J1's shell spans z 0..-3.26 (below the board).
# Tunnel for the plug shell through the wall, plus a slim full-height rim
# notch so the 6.5mm-tall cable overmould (centre z=-1.6) seats the plug fully.
# minimal opening - just the plug, nothing more:
#   tunnel = shell 8.94x3.26 + 0.33/side -> 9.6 x 3.6
#   recess = overmould 12x6.5 + 0.3/side, height-limited (was full tray height)
# absolute minimum: tunnel for the shell + a snug collar recess for a SLIM
# cable overmould (10.5 x 5 typical). Chunky cables will not seat - widen
# usbnotch if yours does not click in.
# overshoot far through both faces - a flush-ended cut left a zero-thickness
# membrane sealing the lower half of the port
# (USB port is cut AFTER the edge bevel - see below - so the bevel cannot
# choke the small opening)
print("  USB slot %.1f mm wide, z %.2f..%.2f (%.2f tall), flared to %.1f mm at the mouth"
      % (USB_X[1] - USB_X[0], USB_Z_BOTTOM, LID_Z[1], LID_Z[1] - USB_Z_BOTTOM,
         FLARE_X[1] - FLARE_X[0]))
for i, (cx, cy) in enumerate(SCREWS):
    add(tray, cylinder("boss%d" % i, cx, cy, BOSS_D, tlo + FLOOR, BOSS_TOP))
for i, (cx, cy) in enumerate(SCREWS):
    cut(tray, cylinder("ins%d" % i, cx, cy, INSERT_D, BOSS_TOP - INSERT_L - 0.4, BOSS_TOP + 1))
# strip any zero-area membranes the booleans left behind
import bmesh as _bm
_b = _bm.new(); _b.from_mesh(tray.data)
_bm.ops.remove_doubles(_b, verts=_b.verts, dist=1e-6)
_deg = [f for f in _b.faces if f.calc_area() < 1e-10]
if _deg:
    _bm.ops.delete(_b, geom=_deg, context='FACES')
_b.to_mesh(tray.data); _b.free(); tray.data.update()
print("tray membranes cleaned:", len(_deg))
print("tray: pocket + %d bosses, top at z=%.1f (PCB underside), %.1f mm tall"
      % (len(SCREWS), BOSS_TOP, BOSS_TOP - (tlo + FLOOR)))
print("  insert bore %.2f dia x %.2f deep for %s" % (INSERT_D, INSERT_L + 0.4, INSERT))

# ---------------------------------------------------------------- cover cap
capobj = cylinder("CoverCap", 0.0, 0.0, COVER_D, 0.0, COVER_H)
print("cover cap: %.2f dia x %.2f thick (0.20 mm clearance in the %.2f bore)"
      % (COVER_D, COVER_H, CBORE_D))

for o in scratch:
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- soften edges
# 0.6mm bevel on every edge sharper than 40deg: outer corners, cutout rims,
# the USB port mouth - printed parts read as moulded instead of machined
for o in (lid, tray, capobj):
    bpy.context.view_layer.objects.active = o
    bv = o.modifiers.new("soften", 'BEVEL')
    bv.width = 0.0006
    bv.segments = 3
    bv.limit_method = 'ANGLE'
    bv.angle_limit = 0.698  # 40 deg
    bpy.ops.object.modifier_apply(modifier=bv.name)
print("edges softened: 0.6mm bevel, 3 segments")

# USB port cut post-bevel: a 0.6mm bevel on a 3.6mm opening would choke it
# to ~2.4mm effective - smaller than the plug shell. Cut after so the port
# edges stay crisp and full-size.
cut(tray, box("usbport", 40.203, 49.797, -9.013, -1.007, -3.453, 0.147))
cut(tray, box("usbnotch", 39.303, 50.697, -5.213, -2.847, -4.403, 0.997))
print("USB port cut post-bevel (crisp, full-size)")

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
    print("   -> %s" % path)

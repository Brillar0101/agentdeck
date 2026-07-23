"""Build the full ClaudeMicro assembly in Blender: board + switches + caps +
knob + joystick cap + two-part case, positioned from the live PCB.

Run headless:  Blender -b --python tools/build_assembly.py
Inputs:  /tmp/ClaudeMicro_sw.glb (board glb exported WITH switch models)
         /tmp/positions.json     (key/control/USB positions from the board)
Output:  enclosure/ClaudeMicro-v3-assembled.blend + case STLs
"""
import bpy, math, json
from mathutils import Vector, Matrix

MM = 0.001
ROOT = "/Users/barakaeli/kicad-projects/claude-micro/"
KC, ENC, JOY = ROOT + "enclosure/keycaps/", ROOT + "enclosure/encoder/", ROOT + "enclosure/joystick/"
pos = json.load(open("/tmp/positions.json"))
USB_ON_TOP = pos["usb"]["top"]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath="/tmp/ClaudeMicro_sw.glb")


def stl(path):
    before = set(bpy.data.objects)
    try: bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
    except AttributeError: bpy.ops.import_mesh.stl(filepath=path, global_scale=0.001)
    return [o for o in bpy.data.objects if o not in before][0]


def wcen(o):
    p = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector((sum(v.x for v in p)/8, sum(v.y for v in p)/8, min(v.z for v in p)))


# ---- seat switches: tall meshes centred on a key position ----
keypts = [(kx*MM, -ky*MM) for kx, ky in pos["keys"].values()]
switches = []
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    p = [o.matrix_world @ Vector(c) for c in o.bound_box]
    w = max(v.x for v in p)-min(v.x for v in p); d = max(v.y for v in p)-min(v.y for v in p)
    zt = max(v.z for v in p); cx = sum(v.x for v in p)/8; cy = sum(v.y for v in p)/8
    if zt > 0.006 and 0.010 < w < 0.020 and 0.010 < d < 0.020 and \
       any(math.hypot(cx-kx, cy-ky) < 0.004 for kx, ky in keypts):
        switches.append(o)
for o in switches:
    c = wcen(o)
    o.matrix_world = Matrix.Translation(Vector((c.x, c.y, 0))) @ Matrix.Rotation(math.radians(180), 4, 'Z') \
                     @ Matrix.Translation(Vector((-c.x, -c.y, 0))) @ o.matrix_world
    bpy.context.view_layer.update()
    c = wcen(o)
    o.matrix_world = Matrix.Translation(Vector((0, 0, -0.00116 - c.z))) @ o.matrix_world
    bpy.context.view_layer.update()
print("switches seated:", len(switches))

# ---- keycaps ----
CAP_TOP = 0.01188
mat = bpy.data.materials.new("CapMat"); mat.use_nodes = True
bs = mat.node_tree.nodes.get("Principled BSDF")
bs.inputs["Base Color"].default_value = (0.93, 0.93, 0.96, 1); bs.inputs["Roughness"].default_value = 0.5
tpl = {}
for kind, fn in (("normal", "cap-normal.stl"), ("groove", "cap-groove.stl"), ("large", "cap-large.stl")):
    o = stl(KC + fn); o.name = "Tpl_" + kind
    if not o.data.materials: o.data.materials.append(mat)
    tpl[kind] = o


def seat_cap(kind, kx, ky, name, xscale=1.0):
    o = tpl[kind].copy(); o.data = tpl[kind].data.copy() if xscale != 1 else tpl[kind].data
    bpy.context.scene.collection.objects.link(o); o.name = name
    if xscale != 1:
        p = [o.matrix_world @ Vector(c) for c in o.bound_box]
        cx = sum(v.x for v in p)/8; cy = sum(v.y for v in p)/8
        o.matrix_world = Matrix.Translation(Vector((cx, cy, 0))) @ Matrix.Scale(xscale, 4, Vector((1, 0, 0))) \
                         @ Matrix.Translation(Vector((-cx, -cy, 0))) @ o.matrix_world
    bpy.context.view_layer.update()
    p = [o.matrix_world @ Vector(c) for c in o.bound_box]
    cx = sum(v.x for v in p)/8; cy = sum(v.y for v in p)/8; zt = max(v.z for v in p)
    o.matrix_world = Matrix.Translation(Vector((kx*MM-cx, -ky*MM-cy, CAP_TOP-zt))) @ o.matrix_world


GROOVE = {"SW4", "SW5"}
for ref, (kx, ky) in pos["keys"].items():
    if ref == "SW11": seat_cap("large", kx, ky, "Cap_GO", xscale=35.9/27.43)
    else: seat_cap("groove" if ref in GROOVE else "normal", kx, ky, f"Cap_{ref}")
for t in tpl.values(): bpy.data.objects.remove(t, do_unlink=True)
print("caps placed:", len(pos["keys"]))

# ---- encoder knob ----
kmat = bpy.data.materials.new("KnobMat"); kmat.use_nodes = True
kb = kmat.node_tree.nodes.get("Principled BSDF")
kb.inputs["Base Color"].default_value = (0.08, 0.08, 0.09, 1)
kb.inputs["Roughness"].default_value = 0.35; kb.inputs["Metallic"].default_value = 0.7
knob = stl(ENC + "d19h20-knurled-encoder-knobs-champfered-top.stl"); knob.name = "EncoderKnob"
knob.data.materials.append(kmat)
c = wcen(knob)
knob.matrix_world = Matrix.Translation(Vector((c.x, c.y, c.z+0.010))) @ Matrix.Rotation(math.radians(90), 4, 'X') \
                    @ Matrix.Translation(Vector((-c.x, -c.y, -(c.z+0.010)))) @ knob.matrix_world
bpy.context.view_layer.update()
ex, ey = pos["ctrl"]["ENC1"]
c = wcen(knob)
knob.matrix_world = Matrix.Translation(Vector((ex*MM-c.x, -ey*MM-c.y, 0.009-c.z))) @ knob.matrix_world
print("knob at", ex, ey)

# ---- joystick cap ----
jc = stl(JOY + "JoyCap.stl"); jc.name = "JoyCap"; jc.data.materials.append(kmat)
jx, jy = pos["ctrl"]["JS1"]
c = wcen(jc)
jc.matrix_world = Matrix.Translation(Vector((jx*MM-c.x, -jy*MM-c.y, 0.0088-c.z))) @ jc.matrix_world
print("joycap at", jx, jy)

# ---- case ----
def box(x0, x1, y0, y1, z0, z1):
    bpy.ops.mesh.primitive_cube_add(); o = bpy.context.active_object
    o.location = ((x0+x1)/2*MM, -(y0+y1)/2*MM, (z0+z1)/2*MM)
    o.scale = ((x1-x0)/2*MM, (y1-y0)/2*MM, (z1-z0)/2*MM)
    bpy.ops.object.transform_apply(scale=True); return o


def cyl(x, y, z0, z1, r, v=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r*MM, depth=(z1-z0)*MM, vertices=v)
    o = bpy.context.active_object; o.location = (x*MM, -y*MM, (z0+z1)/2*MM); return o


def bl(t, tool, op):
    m = t.modifiers.new("b", 'BOOLEAN'); m.operation = op; m.object = tool
    bpy.context.view_layer.objects.active = t; bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def rbox(x0, x1, y0, y1, z0, z1, r):
    o = box(x0+r, x1-r, y0, y1, z0, z1); bl(o, box(x0, x1, y0+r, y1-r, z0, z1), 'UNION')
    for cx, cy in ((x0+r, y0+r), (x1-r, y0+r), (x0+r, y1-r), (x1-r, y1-r)):
        bl(o, cyl(cx, cy, z0, z1, r), 'UNION')
    return o


def deisl(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    parts = list(bpy.context.selected_objects)
    main = max(parts, key=lambda p: p.dimensions.x*p.dimensions.y)
    for p in parts:
        if p is not main: bpy.data.objects.remove(p, do_unlink=True)
    return main


WALL, CLR, CAV, FLOOR, TOPZ = 2.6, 0.5, 4.0, 2.4, 13.6
HOLES = [(6, 6), (84, 6), (6, 84), (84, 84)]
bot = rbox(-WALL, 90+WALL, -WALL, 90+WALL, -(CAV+FLOOR), 1.8, 6.0); bot.name = "CaseBottom"
bl(bot, rbox(-CLR, 90+CLR, -CLR, 90+CLR, -CAV, 3.0, 4.0), 'DIFFERENCE')
if USB_ON_TOP:
    bl(bot, rbox(38, 52, -WALL-2, 1, 1.0, 1.8, 1.2), 'DIFFERENCE')
else:
    bl(bot, rbox(38, 52, -WALL-2, 1, -3.9, 0.6, 1.2), 'DIFFERENCE')
for hx, hy in HOLES:
    bl(bot, cyl(hx, hy, -CAV, 0, 3.7), 'UNION'); bl(bot, cyl(hx, hy, -4.9, 0.01, 1.75), 'DIFFERENCE')
bmat = bpy.data.materials.new("BotMat"); bmat.diffuse_color = (0.10, 0.10, 0.12, 1)
bot.data.materials.append(bmat)

top = rbox(-WALL, 90+WALL, -WALL, 90+WALL, 1.8, TOPZ, 6.0); top.name = "CaseTop"
H = 18.4/2
for ref, (kx, ky) in pos["keys"].items():
    gw = 36.8/2 if ref == "SW11" else H
    bl(top, rbox(kx-gw, kx+gw, ky-H, ky+H, 1.0, TOPZ+1, 2.0), 'DIFFERENCE')
bl(top, cyl(ex, ey, 1.0, TOPZ+1, 10.75), 'DIFFERENCE')
bl(top, cyl(jx, jy, 1.0, TOPZ+1, 12.0), 'DIFFERENCE')
if USB_ON_TOP:
    bl(top, box(38, 52, -WALL-2, 3, 1.0, 5.5), 'DIFFERENCE')
for hx, hy in HOLES:
    bl(top, cyl(hx, hy, 1.6, 1.8, 3.5), 'UNION')
    bl(top, cyl(hx, hy, 0.5, TOPZ+1, 1.4), 'DIFFERENCE')
    bl(top, cyl(hx, hy, 5.5, TOPZ+1, 2.7), 'DIFFERENCE')
top = deisl(top); top.name = "CaseTop"
tmat = bpy.data.materials.new("TopMat"); tmat.diffuse_color = (0.16, 0.16, 0.19, 1)
top.data.materials.append(tmat)
print("case built (USB on top:", USB_ON_TOP, ")")


def exp(o, p):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    try: bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True, global_scale=1000.0)
    except AttributeError: bpy.ops.export_mesh.stl(filepath=p, use_selection=True, global_scale=1000.0)


exp(bot, ROOT + "enclosure/ClaudeMicro-v3-case-bottom.stl")
exp(top, ROOT + "enclosure/ClaudeMicro-v3-case-top.stl")
top.hide_set(True); top.hide_viewport = True; top.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "enclosure/ClaudeMicro-v3-assembled.blend")
print("V3 ASSEMBLED DONE")

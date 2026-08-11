"""Dress the V3 assembly: real fastener meshes + natural PBR materials + render.

Adds to v3/enclosure/AgentDeckV3-assembled.blend:
  * 6x M2.5x8 countersunk screws (ISO 7046: 90 deg head O5.0, shank O2.45)
    seated flush in the lid countersinks, tips inside the inserts
  * 6x brass heat-set inserts (OD 4.0 x 4.0) in the bottom-case bosses
  * PBR materials: matte ABS cases/plugs, steel screws, brass inserts,
    silicone battery wrap (keycaps/knob already PBR; board comes textured
    from the KiCad GLB export)
  * a lit camera + EEVEE preview render -> AgentDeckV3-preview.png

Run:  blender -b --python v3/tools/dress_assembly.py
"""
import json
import math

import bpy
from mathutils import Vector

MM = 0.001
ROOT = "/Users/barakaeli/kicad-projects/agentdeck/"
BLEND = ROOT + "v3/enclosure/AgentDeckV3-assembled.blend"
PREVIEW = ROOT + "v3/enclosure/AgentDeckV3-preview.png"
pos = json.load(open(ROOT + "v3/enclosure/positions.json"))
HOLES = [tuple(v) for _, v in sorted(pos["holes"].items())] if "holes" in pos \
    else [(6, 6), (144, 6), (6, 104), (144, 104), (6, 55), (144, 55)]

# case stack (make_case_v3.py)
CS_START, CS_END = 2.95, 4.0        # countersink; head top flush at 4.0
HEAD_D, SHANK_D, SCREW_LEN = 5.0, 2.45, 8.0
INS_OD, INS_ID, INS_LEN = 4.0, 2.1, 4.0

bpy.ops.wm.open_mainfile(filepath=BLEND)


def pbr(name, base, rough, metal=0.0, clear=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*base, 1)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    if clear and "Coat Weight" in bs.inputs:
        bs.inputs["Coat Weight"].default_value = clear
    m.diffuse_color = (*base, 1)
    return m


M_BOT = pbr("PlasticBottom", (0.045, 0.045, 0.055), 0.62)
M_TOP = pbr("PlasticTop", (0.055, 0.055, 0.068), 0.52, clear=0.12)
M_STEEL = pbr("ScrewSteel", (0.42, 0.42, 0.45), 0.28, metal=1.0)
M_BRASS = pbr("InsertBrass", (0.80, 0.58, 0.22), 0.42, metal=1.0)
M_BATT = pbr("BatterySilver", (0.62, 0.63, 0.66), 0.35, metal=0.85)


def assign(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)


for o in bpy.data.objects:
    n = o.name.lower()
    if o.type != 'MESH':
        continue
    if n.startswith("casebottom"):
        assign(o, M_BOT)
    elif n.startswith("casetop") or n.startswith("coverplug"):
        assign(o, M_TOP)
    elif "battery" in n:
        assign(o, M_BATT)


def cyl(x, y, z0, z1, r, v=48):
    bpy.ops.mesh.primitive_cylinder_add(radius=r * MM, depth=(z1 - z0) * MM,
                                        vertices=v)
    o = bpy.context.active_object
    o.location = (x * MM, -y * MM, (z0 + z1) / 2 * MM)
    return o


def cone(x, y, z0, z1, r_bot, r_top, v=48):
    bpy.ops.mesh.primitive_cone_add(radius1=r_bot * MM, radius2=r_top * MM,
                                    depth=(z1 - z0) * MM, vertices=v)
    o = bpy.context.active_object
    o.location = (x * MM, -y * MM, (z0 + z1) / 2 * MM)
    return o


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


# the assembly builder hides the lid for board inspection - this scene is the
# fully ASSEMBLED view: show the top case everywhere (viewport + render)
for o in bpy.data.objects:
    if o.name.startswith(("CaseTop", "CoverPlug")):
        o.hide_set(False)
        o.hide_viewport = False
        o.hide_render = False

# drop any previous fastener meshes (idempotent re-run)
for o in list(bpy.data.objects):
    if o.name.startswith(("Screw_", "Insert_")):
        bpy.data.objects.remove(o, do_unlink=True)

for i, (hx, hy) in enumerate(HOLES):
    head = cone(hx, hy, CS_START, CS_END, SHANK_D / 2, HEAD_D / 2)
    shank = cyl(hx, hy, CS_END - SCREW_LEN, CS_START + 0.05, SHANK_D / 2)
    # hex socket recess suggestion: shallow dark cylinder on the head top
    sock = cyl(hx, hy, CS_END - 0.6, CS_END + 0.001, 1.0, v=6)
    screw = join([head, shank, sock], f"Screw_{i}")
    assign(screw, M_STEEL)

    outer = cyl(hx, hy, -INS_LEN, -0.05, INS_OD / 2)
    ins = join([outer], f"Insert_{i}")
    assign(ins, M_BRASS)
print(f"fasteners: {len(HOLES)} screws M2.5x{SCREW_LEN} + {len(HOLES)} inserts")

# ---------------- camera + light + preview render ----------------
for o in list(bpy.data.objects):
    if o.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o, do_unlink=True)

cx, cy = 75 * MM, -55 * MM              # board centre in Blender coords
bpy.ops.object.camera_add(location=(cx - 0.16, cy - 0.20, 0.19))
cam = bpy.context.active_object
direction = Vector((cx, cy, 0.005)) - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 45
bpy.context.scene.camera = cam

bpy.ops.object.light_add(type='SUN', location=(cx - 0.1, cy - 0.1, 0.4))
sun = bpy.context.active_object
sun.data.energy = 2.2
sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(-30))
bpy.ops.object.light_add(type='AREA', location=(cx + 0.12, cy + 0.10, 0.25))
fill = bpy.context.active_object
fill.data.energy = 35.0
fill.data.size = 0.4
w = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.9, 0.9, 0.92, 1)
    bg.inputs[1].default_value = 0.35

sc = bpy.context.scene
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
sc.render.resolution_x, sc.render.resolution_y = 1440, 1080
sc.render.filepath = PREVIEW

bpy.ops.wm.save_mainfile()
bpy.ops.render.render(write_still=True)
print("DRESSED + RENDERED:", PREVIEW)

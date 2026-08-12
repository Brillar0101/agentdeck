"""Assemble the V2 case + board into a .blend for inspection."""
import math
import os

import bpy
from mathutils import Vector

ROOT = "/Users/barakaeli/kicad-projects/claude-micro/v2/enclosure"

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

def import_stl(path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
    else:
        bpy.ops.import_mesh.stl(filepath=path, global_scale=0.001)
    return [o for o in bpy.data.objects if o not in before]

lid = import_stl(f"{ROOT}/case-top-lid.stl")[0]
lid.name = "CaseTop"
tray = import_stl(f"{ROOT}/case-bottom.stl")[0]
tray.name = "CaseBottom"

# STL was exported with global_scale=1000 from metres, so it is in mm; the
# generator's frame is x=pcb_x, y=-pcb_y, z=pcb_z. Import scale 0.001 puts us
# back in metres in that same frame. Nothing to move - both parts are in place.

# materials
white = bpy.data.materials.new("CaseWhite")
white.use_nodes = True
bsdf = white.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.92, 0.92, 0.93, 1)
bsdf.inputs["Roughness"].default_value = 0.45
for o in (lid, tray):
    o.data.materials.clear()
    o.data.materials.append(white)

# cover caps at the four counterbores (top of lid z=8.4, cbore depth 2.5 ->
# cap sits at z 7.2..8.4 nominal; place base at counterbore floor 5.9+1.3 head)
cap_src = import_stl(f"{ROOT}/case-cover-plug.stl")[0]
SCREWS = [(6.0, 6.0), (106.0, 6.0), (6.0, 106.0), (106.0, 106.0)]
capm = bpy.data.materials.new("CapWhite")
capm.use_nodes = True
capm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.91, 1)
cap_src.data.materials.clear()
cap_src.data.materials.append(capm)
for i, (sx, sy) in enumerate(SCREWS):
    c = cap_src.copy()
    c.name = f"CoverCap_{i}"
    c.location = Vector((sx / 1000.0, -sy / 1000.0, 0.0072))
    bpy.context.scene.collection.objects.link(c)
bpy.data.objects.remove(cap_src, do_unlink=True)

# board
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=f"{ROOT}/AgentDeckV2-board.glb")
board_objs = [o for o in bpy.data.objects if o not in before]
root = None
for o in board_objs:
    if o.parent is None:
        root = o
        break
# align board bbox to (0..0.112, -0.112..0, 0..0.0016 plus component heights)
bpy.context.view_layer.update()
mins = Vector((1e9, 1e9, 1e9)); maxs = Vector((-1e9, -1e9, -1e9))
for o in board_objs:
    if o.type != 'MESH':
        continue
    for corner in o.bound_box:
        w = o.matrix_world @ Vector(corner)
        mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
size = maxs - mins
print("board glb bbox mm:", [round(v * 1000, 1) for v in size])
# board substrate is the dominant xy span = 112 x 112; move so pcb top face
# lands at z=0.0016 and xy corner at (0, -0.112)
off = Vector((0 - mins.x, -0.112 - mins.y, 0.0)) 
# z: kicad glb puts pcb bottom at local min for the substrate; components
# extend both sides. The substrate spans 1.6mm; find it: use the largest mesh
sub = max((o for o in board_objs if o.type == 'MESH'),
          key=lambda o: (o.dimensions.x * o.dimensions.y))
sb_min = min((sub.matrix_world @ Vector(c)).z for c in sub.bound_box)
off.z = 0.0 - sb_min
if root is not None:
    root.location += off
else:
    for o in board_objs:
        if o.parent is None:
            o.location += off
bpy.context.view_layer.update()
print("board aligned")

bpy.ops.wm.save_as_mainfile(filepath=f"{ROOT}/AgentDeckV2-assembled.blend")
print("SAVED", f"{ROOT}/AgentDeckV2-assembled.blend")

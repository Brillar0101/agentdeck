#!/usr/bin/env python3
"""Post-route GND stitching (graph-based).

Model every GND pour fragment (both layers) as a node and every GND via as
an edge between the fragments it lands in. For each connected component
that does not include the main sheet, place a new via at a point inside one
of its fragments where the OTHER layer's main-component copper also exists,
merging the component in. Sub-3mm2 slivers are purged via area-based island
removal. Iterates until fully merged or no candidate spot remains.

Run after SES import, with KiCad's bundled python:
  .../Versions/Current/bin/python3 tools/stitch_islands.py
"""
import os
import pcbnew

H = os.path.expanduser("~/kicad-projects/claude-micro")
MM = pcbnew.FromMM
MIN_ISLAND_MM2 = 3.0
MARGIN = 0.2          # via clearance to island edge, mm


def fragments(board, gnd_code):
    """[(layer, sps, outline_idx)] for every filled GND fragment."""
    out = []
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetCode() != gnd_code:
            continue
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.IsOnLayer(layer):
                continue
            sps = z.GetFilledPolysList(layer)
            for i in range(sps.OutlineCount()):
                out.append((layer, sps, i))
    return out


def components(frags, vias):
    parent = list(range(len(frags)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    for v in vias:
        touched = [k for k, (lay, sps, i) in enumerate(frags)
                   if sps.Contains(v.GetPosition(), i)]
        for a, b in zip(touched, touched[1:]):
            union(a, b)
    groups = {}
    for k in range(len(frags)):
        groups.setdefault(find(k), []).append(k)
    return list(groups.values())


def in_no_via_area(board, px, py):
    pt = pcbnew.VECTOR2I(MM(px), MM(py))
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            if z.Outline().Contains(pt):
                return True
    return False


def spot_in_both(frags, k_small, k_big):
    """Grid point inside fragment k_small that also lies in k_big."""
    lay_s, sps_s, i_s = frags[k_small]
    lay_b, sps_b, i_b = frags[k_big]
    if lay_s == lay_b:
        return None
    bb = sps_s.Outline(i_s).BBox()
    w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    steps = 24
    for gy in range(1, steps):
        for gx in range(1, steps):
            px, py = x0 + w * gx / steps, y0 + h * gy / steps
            ok = all(sps.Contains(pcbnew.VECTOR2I(MM(px + dx), MM(py + dy)), i)
                     for (sps, i) in ((sps_s, i_s), (sps_b, i_b))
                     for dx in (-MARGIN, 0, MARGIN) for dy in (-MARGIN, 0, MARGIN))
            if ok:
                return (px, py)
    return None


def main():
    board = pcbnew.LoadBoard(f"{H}/ClaudeMicro.kicad_pcb")
    gnd = board.FindNet("GND")
    gnd_code = gnd.GetNetCode()
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetCode() == gnd_code:
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
            z.SetMinIslandArea(int(MIN_ISLAND_MM2 * 1e12))   # nm^2

    total_added = 0
    for round_ in range(6):
        frags = fragments(board, gnd_code)
        vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"
                and t.GetNetCode() == gnd_code]
        comps = components(frags, vias)
        main_comp = max(comps, key=lambda c: sum(
            frags[k][1].Outline(frags[k][2]).BBox().GetArea() for k in c))
        orphans = [c for c in comps if c is not main_comp]
        if not orphans:
            break
        added = 0
        for comp in orphans:
            done = False
            for k_small in comp:
                for k_big in main_comp:
                    spot = spot_in_both(frags, k_small, k_big)
                    if spot and in_no_via_area(board, *spot):
                        spot = None
                    if spot:
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(pcbnew.VECTOR2I(MM(spot[0]), MM(spot[1])))
                        v.SetWidth(MM(0.6))
                        v.SetDrill(MM(0.3))
                        v.SetNet(gnd)
                        board.Add(v)
                        added += 1
                        done = True
                        break
                if done:
                    break
            if not done:
                sizes = [f"{pcbnew.ToMM(frags[k][1].Outline(frags[k][2]).BBox().GetWidth()):.1f}x"
                         f"{pcbnew.ToMM(frags[k][1].Outline(frags[k][2]).BBox().GetHeight()):.1f}"
                         for k in comp]
                print(f"  round {round_}: component unmergeable {sizes}")
        total_added += added
        board.BuildListOfNets()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        if added == 0:
            break
    pcbnew.SaveBoard(f"{H}/ClaudeMicro.kicad_pcb", board)
    frags = fragments(board, gnd_code)
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"
            and t.GetNetCode() == gnd_code]
    print(f"added {total_added} vias; final components: {len(components(frags, vias))}")


main()

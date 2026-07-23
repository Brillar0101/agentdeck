#!/usr/bin/env python3
"""Generate ClaudeMicro.kicad_sch section by section.

Claude Micro — desk controller for Claude Code (RP2040 + QMK).
Every circuit block follows its datasheet's required application circuit;
see DESIGN.md "Datasheet-required practices" for sources and rationale.

Coordinates: sheet mm, 1.27 grid, y DOWN, paper A2. Symbols placed at
angle 0, no mirror: pin at symbol-local (lx, ly) maps to (px+lx, py-ly).
Pin coordinates are parsed from the symbol libraries automatically.
"""
import re
import uuid

ROOT_UUID = "c1a0de00-0001-4000-8000-000000000001"
PROJECT = "ClaudeMicro"

KSYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
DEVICE_LIB = f"{KSYM}/Device.kicad_sym"
POWER_LIB = f"{KSYM}/power.kicad_sym"
CONN_LIB = f"{KSYM}/Connector_Generic.kicad_sym"
JLC_LIB = "JLC.kicad_sym"

LIBSYMS = {
    "Device:R": (DEVICE_LIB, "R"),
    "Device:C": (DEVICE_LIB, "C"),
    "ClaudeMicro_Custom:SKQUCAA010": ("ClaudeMicro_Custom.kicad_sym", "SKQUCAA010"),
    "ClaudeMicro_Custom:TouchPad": ("ClaudeMicro_Custom.kicad_sym", "TouchPad"),
    "ClaudeMicro_Custom:ProgPads_1x4": ("ClaudeMicro_Custom.kicad_sym", "ProgPads_1x4"),
    "power:GND": (POWER_LIB, "GND"),
    "power:+3V3": (POWER_LIB, "+3V3"),
    "power:VBUS": (POWER_LIB, "VBUS"),
    "power:PWR_FLAG": (POWER_LIB, "PWR_FLAG"),
    "JLC:RP2040": (JLC_LIB, "RP2040"),
    "JLC:W25Q128JVSIQTR": (JLC_LIB, "W25Q128JVSIQTR"),
    "JLC:AMS1117-3.3": (JLC_LIB, "AMS1117-3.3"),
    "JLC:TYPE-C-31-M-12": (JLC_LIB, "TYPE-C-31-M-12"),
    "JLC:USBLC6-2SC6": (JLC_LIB, "USBLC6-2SC6"),
    "JLC:ABM8-272-T3_C20625731": (JLC_LIB, "ABM8-272-T3_C20625731"),
    "JLC:SN74AHCT1G125DBVR": (JLC_LIB, "SN74AHCT1G125DBVR"),
    "JLC:SK6812MINI-E_C5149201": (JLC_LIB, "SK6812MINI-E_C5149201"),
    "JLC:TTP223-BA6": (JLC_LIB, "TTP223-BA6"),
    "JLC:CPG135001S30": (JLC_LIB, "CPG135001S30"),
    "JLC:EC11E1834403": (JLC_LIB, "EC11E1834403"),
    "JLC:TS-1187A-B-A-B": (JLC_LIB, "TS-1187A-B-A-B"),
    "JLC:KT-0603R": (JLC_LIB, "KT-0603R"),
}


def extract_block(path, name):
    s = open(path).read()
    i = s.find(f'(symbol "{name}"')
    if i < 0:
        raise SystemExit(f"symbol {name} not found in {path}")
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    return s[i:j + 1]


def parse_pins(block):
    """number -> (lx, ly) from a symbol block."""
    out = {}
    for m in re.finditer(
            r'\(pin \S+ \S+\s*\(at ([-\d.]+) ([-\d.]+) [\d.]+\).*?'
            r'\(number "([^"]+)"', block, re.S):
        out[m.group(3)] = (float(m.group(1)), float(m.group(2)))
    return out


PIN_XY = {}
_blocks = {}
for lib_id, (path, name) in LIBSYMS.items():
    blk = extract_block(path, name)
    _blocks[lib_id] = blk.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)
    PIN_XY[lib_id] = parse_pins(blk)

# ref -> footprint
FP = {
    "U1": "JLC:LQFN-56_L7.0-W7.0-P0.4-EP",
    "U2": "JLC:SOIC-8_L5.3-W5.3-P1.27-LS8.0-BL",
    "U3": "JLC:SOT-223-3_L6.5-W3.4-P2.30-LS7.0-BR",
    "U4": "JLC:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR",
    "U5": "JLC:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
    "U6": "JLC:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
    "J1": "JLC:USB-C_SMD-TYPE-C-31-M-12_1",
    "J2": "ClaudeMicro:ProgPads_1x4",
    "JS1": "ClaudeMicro:SKQUCAA010",
    "TP1": "ClaudeMicro:TouchPad_D12",
    "Y1": "JLC:CRYSTAL-SMD_4P-L3.2-W2.5-BL",
    "ENC1": "JLC:SW-TH_EC11E1820402",
    "SW13": "JLC:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
}
for n in range(1, 13):
    FP[f"SW{n}"] = "JLC:CONN-SMD_HOTPLUGPAKAGE__C9900010116"
for n in list(range(1, 7)) + list(range(10, 16)):
    FP[f"D{n}"] = "JLC:LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E"
for n in range(7, 10):
    FP[f"D{n}"] = "JLC:LED-SMD_L1.6-W0.8-R-RD"
for n in range(1, 13):
    FP[f"R{n}"] = "Resistor_SMD:R_0603_1608Metric"
for n in range(1, 32):
    FP[f"C{n}"] = "Capacitor_SMD:C_0603_1608Metric"

items = []
GRID = 1.27


def u():
    return str(uuid.uuid4())


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def ep(px, py, lib_id, pin):
    lx, ly = PIN_XY[lib_id][pin]
    return (round(snap(px) + lx, 4), round(snap(py) - ly, 4))


def wire(x1, y1, x2, y2):
    items.append(
        f'\t(wire\n\t\t(pts\n\t\t\t(xy {x1} {y1}) (xy {x2} {y2})\n\t\t)\n'
        f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
        f'\t\t(uuid "{u()}")\n\t)')


def no_connect(x, y):
    items.append(f'\t(no_connect\n\t\t(at {x} {y})\n\t\t(uuid "{u()}")\n\t)')


def glabel(text, x, y, angle=0, justify="left"):
    items.append(
        f'\t(global_label "{text}"\n\t\t(shape bidirectional)\n\t\t(at {x} {y} {angle})\n'
        f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {justify})\n\t\t)\n'
        f'\t\t(uuid "{u()}")\n'
        f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
        f'\t\t\t(at {x} {y} 0)\n'
        f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)')


def section_box(x1, y1, x2, y2, title, tx, ty):
    items.append(
        f'\t(rectangle\n\t\t(start {x1} {y1})\n\t\t(end {x2} {y2})\n'
        f'\t\t(stroke\n\t\t\t(width 0.1524)\n\t\t\t(type dash)\n\t\t\t(color 0 0 0 1)\n\t\t)\n'
        f'\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "{u()}")\n\t)')
    items.append(
        f'\t(text "{title}"\n\t\t(exclude_from_sim no)\n\t\t(at {tx} {ty} 0)\n'
        f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 2.0 2.0)\n\t\t\t\t(thickness 0.4)\n\t\t\t\t(bold yes)\n'
        f'\t\t\t\t(color 30 90 180 1)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{u()}")\n\t)')


def prop(name, value, x, y, angle=0, justify=None, hide=False):
    j = f'\n\t\t\t\t(justify {justify})' if justify else ''
    h = '\n\t\t\t(hide yes)' if hide else ''
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {x} {y} {angle})\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){j}\n\t\t\t){h}\n\t\t)')


def place(lib_id, ref, value, x, y, pins, dnp=False):
    x, y = snap(x), snap(y)
    pin_lines = '\n'.join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{u()}")\n\t\t)' for p in pins)
    props = '\n'.join([
        prop("Reference", ref, x + 2.54, y - 1.27, 0, "left"),
        prop("Value", value, x + 2.54, y + 1.27, 0, "left"),
        prop("Footprint", FP.get(ref, ""), x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])
    dnp_s = 'yes' if dnp else 'no'
    items.append(
        f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
        f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp {dnp_s})\n'
        f'\t\t(uuid "{u()}")\n{props}\n{pin_lines}\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


PWR_N = [0]
PWR_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VBUS": "power:VBUS"}


def pwr(net, x, y):
    PWR_N[0] += 1
    ref = f"#PWR0{PWR_N[0]:03d}"
    vy = y + 3.302 if net == "GND" else y - 3.302
    x, y = snap(x), snap(y)
    props = '\n'.join([
        prop("Reference", ref, x, y, 0, hide=True),
        prop("Value", net, x, vy),
        prop("Footprint", "", x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])
    items.append(
        f'\t(symbol\n\t\t(lib_id "{PWR_LIB[net]}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
        f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
        f'\t\t(uuid "{u()}")\n{props}\n\t\t(pin "1"\n\t\t\t(uuid "{u()}")\n\t\t)\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


FLG_N = [0]


def pwr_flag_at(x, y):
    FLG_N[0] += 1
    ref = f"#FLG0{FLG_N[0]}"
    x, y = snap(x), snap(y)
    props = '\n'.join([
        prop("Reference", ref, x, y - 2.54, 0, hide=True),
        prop("Value", "PWR_FLAG", x, y - 2.54, 0),
        prop("Footprint", "", x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])
    items.append(
        f'\t(symbol\n\t\t(lib_id "power:PWR_FLAG")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)\n'
        f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
        f'\t\t(uuid "{u()}")\n{props}\n\t\t(pin "1"\n\t\t\t(uuid "{u()}")\n\t\t)\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def tap_dir(spec, x, y, side, length=2.54):
    if spec[0] == 'nc':
        no_connect(x, y)
        return
    dx, dy = {'L': (-length, 0), 'R': (length, 0), 'U': (0, -length), 'D': (0, length)}[side]
    ex, ey = round(x + dx, 4), round(y + dy, 4)
    if dx or dy:
        wire(x, y, ex, ey)
    if spec[0] == 'gnd':
        pwr("GND", ex, ey)
    elif spec[0] == 'pwr':
        pwr(spec[1], ex, ey)
    else:
        just = {'L': 'right', 'R': 'left', 'U': 'left', 'D': 'left'}[side]
        glabel(spec[1], ex, ey, 0, just)


def part_taps(lib_id, ref, value, x, y, spec_map, default_side='L', dnp=False):
    """Place a part and tap every pin per spec_map {pin: spec}."""
    place(lib_id, ref, value, x, y, list(PIN_XY[lib_id].keys()), dnp=dnp)
    for pn, (lx, ly) in PIN_XY[lib_id].items():
        if pn not in spec_map:
            continue
        px, py = ep(x, y, lib_id, pn)
        spec, side = spec_map[pn] if isinstance(spec_map[pn], tuple) and len(spec_map[pn]) == 2 and isinstance(spec_map[pn][1], str) and spec_map[pn][1] in 'LRUD' else (spec_map[pn], None)
        if side is None:
            side = 'L' if lx < 0 else ('R' if lx > 0 else ('D' if ly < 0 else 'U'))
        tap_dir(spec, px, py, side)


def rc_net(lib_id, ref, val, x, y, top_spec, bot_spec, dnp=False):
    place(lib_id, ref, val, x, y, ["1", "2"], dnp=dnp)
    t = ep(x, y, lib_id, "1")
    b = ep(x, y, lib_id, "2")
    tap_dir(top_spec, t[0], t[1], 'U')
    tap_dir(bot_spec, b[0], b[1], 'D')


# ============================================================ SECTION 1
# POWER — USB-C in, CC pulldowns, ESD, AMS1117 LDO (10uF in/out per DS)
def section_power():
    section_box(26, 30, 240, 120, "POWER  (USB-C 5V -> AMS1117 -> 3V3; SK6812 rail = VBUS)", 28, 28)

    usb = "JLC:TYPE-C-31-M-12"
    ux, uy = 60.0, 72.0
    part_taps(usb, "J1", "USB-C", ux, uy, {
        "A1B12": ("gnd",), "B1A12": ("gnd",),
        "A4B9": ("pwr", "VBUS"), "B4A9": ("pwr", "VBUS"),
        "A5": ("lbl", "CC1"), "B5": ("lbl", "CC2"),
        "A6": ("lbl", "USB_DP_CONN"), "B6": ("lbl", "USB_DP_CONN"),
        "A7": ("lbl", "USB_DM_CONN"), "B7": ("lbl", "USB_DM_CONN"),
        "A8": ("nc",), "B8": ("nc",),
        "1": ("gnd",), "2": ("gnd",), "3": ("gnd",), "4": ("gnd",),
    })
    # CC pulldowns: 5.1k marks the device as a UFP sink (USB-C spec)
    rc_net("Device:R", "R1", "5.1k", 130.0, 72.0, ("lbl", "CC1"), ("gnd",))
    rc_net("Device:R", "R2", "5.1k", 142.0, 72.0, ("lbl", "CC2"), ("gnd",))

    # AMS1117-3.3: 10uF at input and output (datasheet stability requirement)
    ldo = "JLC:AMS1117-3.3"
    part_taps(ldo, "U3", "AMS1117-3.3", 185.0, 55.0, {
        "3": ("pwr", "VBUS"), "2": ("pwr", "+3V3"), "4": ("pwr", "+3V3"),
        "1": ("gnd",),
    })
    rc_net("Device:C", "C16", "10uF", 165.0, 95.0, ("pwr", "VBUS"), ("gnd",))
    rc_net("Device:C", "C17", "10uF", 180.0, 95.0, ("pwr", "+3V3"), ("gnd",))

    fy = 40.64                                # all grid multiples of 1.27
    for net, fx in (("GND", 209.55), ("VBUS", 220.98), ("+3V3", 231.14)):
        dy = 2.54 if net == "GND" else -2.54
        pwr(net, fx, fy + dy)
        wire(fx, fy + dy, fx, fy)
        pwr_flag_at(fx, fy)

    # USBLC6 ESD on the connector-side D+/D- (pins: 1=IO1 2=GND 3=IO2 4=IO2 5=VBUS 6=IO1)
    esd = "JLC:USBLC6-2SC6"
    part_taps(esd, "U6", "USBLC6-2SC6", 110.0, 105.0, {
        "1": ("lbl", "USB_DM_CONN"), "6": ("lbl", "USB_DM_ESD"),
        "3": ("lbl", "USB_DP_CONN"), "4": ("lbl", "USB_DP_ESD"),
        "5": ("pwr", "VBUS"), "2": ("gnd",),
    })
    # 27R series termination close to RP2040 (RP2040 HW guide 2.4.1)
    rc_net("Device:R", "R3", "27R", 215.0, 105.0, ("lbl", "USB_DP_ESD"), ("lbl", "USB_DP"))
    rc_net("Device:R", "R4", "27R", 228.0, 105.0, ("lbl", "USB_DM_ESD"), ("lbl", "USB_DM"))


# ============================================================ SECTION 2
# MCU — RP2040 (decoupling per HW guide 2.1.2/2.1.3)
def section_mcu():
    section_box(26, 130, 320, 330, "MCU  (RP2040, direct-wired I/O, no matrix)", 28, 128)

    mcu = "JLC:RP2040"
    mx, my = 170.0, 230.0
    spec = {
        # power
        "1": ("pwr", "+3V3"), "10": ("pwr", "+3V3"), "22": ("pwr", "+3V3"),
        "33": ("pwr", "+3V3"), "42": ("pwr", "+3V3"), "49": ("pwr", "+3V3"),
        "48": ("pwr", "+3V3"),                  # USB_VDD
        "43": ("pwr", "+3V3"),                  # ADC_AVDD
        "44": ("pwr", "+3V3"),                  # VREG_IN
        "45": ("lbl", "DVDD"),                  # VREG_VOUT -> DVDD rail
        "50": ("lbl", "DVDD"), "23": ("lbl", "DVDD"),
        "57": ("gnd",),                         # EP/GND
        "19": ("gnd",),                         # TESTEN
        # USB + clock + boot/debug
        "47": ("lbl", "USB_DP"), "46": ("lbl", "USB_DM"),
        "20": ("lbl", "XIN"), "21": ("lbl", "XOUT"),
        "26": ("lbl", "RUN"), "24": ("lbl", "SWCLK"), "25": ("lbl", "SWDIO"),
        # QSPI flash
        "56": ("lbl", "QSPI_SS"), "52": ("lbl", "QSPI_SCLK"),
        "53": ("lbl", "QSPI_SD0"), "54": ("lbl", "QSPI_SD1"),
        "55": ("lbl", "QSPI_SD2"), "51": ("lbl", "QSPI_SD3"),
    }
    # GPIO map (DESIGN.md): 0-11 keys, 12/13/14 encoder, 15-18 joy dirs,
    # 19 joy center, 20 touch, 21 LED data, 22-24 aux LEDs, 25-29 spare
    gpio_pin = {0: "2", 1: "3", 2: "4", 3: "5", 4: "6", 5: "7", 6: "8",
                7: "9", 8: "11", 9: "12", 10: "13", 11: "14", 12: "15",
                13: "16", 14: "17", 15: "18", 16: "27", 17: "28", 18: "29",
                19: "30", 20: "31", 21: "32", 22: "34", 23: "35", 24: "36",
                25: "37", 26: "38", 27: "39", 28: "40", 29: "41"}
    for k in range(12):
        spec[gpio_pin[k]] = ("lbl", f"K{k+1}")
    spec[gpio_pin[12]] = ("lbl", "ENC_A")
    spec[gpio_pin[13]] = ("lbl", "ENC_B")
    spec[gpio_pin[14]] = ("lbl", "ENC_SW")
    for i, d in enumerate(["JOY_A", "JOY_B", "JOY_C", "JOY_D", "JOY_CTR"]):
        spec[gpio_pin[15 + i]] = ("lbl", d)
    spec[gpio_pin[20]] = ("lbl", "TOUCH")
    spec[gpio_pin[21]] = ("lbl", "LED_DATA")
    spec[gpio_pin[22]] = ("lbl", "AUX1")
    spec[gpio_pin[23]] = ("lbl", "AUX2")
    spec[gpio_pin[24]] = ("lbl", "AUX3")
    for g in range(25, 30):
        spec[gpio_pin[g]] = ("nc",)
    part_taps(mcu, "U1", "RP2040", mx, my, spec)

    # decoupling: 100nF per IOVDD/USB_VDD/ADC_AVDD (guide 2.1.2),
    # 1uF at VREG_IN + VREG_OUT (guide 2.1.3)
    for i, cx in enumerate([40, 52, 64, 76, 88, 100, 112, 124]):
        rc_net("Device:C", f"C{5+i}", "100nF", cx, 148.0, ("pwr", "+3V3"), ("gnd",))
    rc_net("Device:C", "C14", "1uF", 136.0, 148.0, ("pwr", "+3V3"), ("gnd",))
    rc_net("Device:C", "C13", "1uF", 148.0, 148.0, ("lbl", "DVDD"), ("gnd",))
    # RUN pull-up + SWD pads
    rc_net("Device:R", "R8", "10k", 296.0, 148.0, ("pwr", "+3V3"), ("lbl", "RUN"))
    hdr = "ClaudeMicro_Custom:ProgPads_1x4"
    part_taps(hdr, "J2", "SWD", 285.0, 300.0, {
        "1": ("lbl", "SWCLK"), "2": ("lbl", "SWDIO"),
        "3": ("gnd",), "4": ("lbl", "RUN"),
    })


# ============================================================ SECTION 3
# FLASH + BOOT (guide 2.2: QSPI_SS 10k pullup DNP, 1k BOOTSEL strap)
def section_flash():
    section_box(330, 30, 470, 120, "FLASH + BOOTSEL", 332, 28)
    fl = "JLC:W25Q128JVSIQTR"
    part_taps(fl, "U2", "W25Q128JVSIQ", 390.0, 65.0, {
        "1": ("lbl", "QSPI_SS"), "6": ("lbl", "QSPI_SCLK"),
        "5": ("lbl", "QSPI_SD0"), "2": ("lbl", "QSPI_SD1"),
        "3": ("lbl", "QSPI_SD2"), "7": ("lbl", "QSPI_SD3"),
        "8": ("pwr", "+3V3"), "4": ("gnd",),
    })
    rc_net("Device:C", "C15", "100nF", 440.0, 60.0, ("pwr", "+3V3"), ("gnd",))
    rc_net("Device:R", "R6", "10k DNP", 452.0, 60.0, ("pwr", "+3V3"), ("lbl", "QSPI_SS"), dnp=True)
    # BOOTSEL: 1k from QSPI_SS to button to GND
    rc_net("Device:R", "R7", "1k", 350.0, 100.0, ("lbl", "QSPI_SS"), ("lbl", "BOOTSEL"))
    sw = "JLC:TS-1187A-B-A-B"
    part_taps(sw, "SW13", "BOOTSEL", 420.0, 105.0, {
        "1": ("lbl", "BOOTSEL"), "3": ("lbl", "BOOTSEL"),
        "2": ("gnd",), "4": ("gnd",),
    })


# ============================================================ SECTION 4
# CRYSTAL (guide 2.3: ABM8-272-T3, 15pF loads, 1k series on XOUT)
def section_crystal():
    section_box(480, 30, 580, 120, "CRYSTAL 12MHz", 482, 28)
    xt = "JLC:ABM8-272-T3_C20625731"
    part_taps(xt, "Y1", "ABM8-272-T3", 520.0, 60.0, {
        "1": ("lbl", "XIN"), "3": ("lbl", "XOUT_XTAL"),
        "2": ("gnd",), "4": ("gnd",),
    })
    rc_net("Device:R", "R5", "1k", 555.0, 60.0, ("lbl", "XOUT"), ("lbl", "XOUT_XTAL"))
    rc_net("Device:C", "C1", "15pF", 500.0, 95.0, ("lbl", "XIN"), ("gnd",))
    rc_net("Device:C", "C2", "15pF", 515.0, 95.0, ("lbl", "XOUT_XTAL"), ("gnd",))


# ============================================================ SECTION 5
# LEDS — 74AHCT1G125 level shifter (SK6812 DS: VIH=0.7*VDD > 3.3V) + chain
def section_leds():
    section_box(330, 130, 580, 232, "KEY LEDS  (VBUS rail, AHCT shift, 12x SK6812MINI-E)", 332, 128)
    ls = "JLC:SN74AHCT1G125DBVR"
    part_taps(ls, "U4", "74AHCT1G125", 360.0, 160.0, {
        "2": ("lbl", "LED_DATA"), "4": ("lbl", "LED_DIN0"),
        "1": ("gnd",), "5": ("pwr", "VBUS"), "3": ("gnd",),
    })
    rc_net("Device:C", "C25", "100nF", 385.0, 155.0, ("pwr", "VBUS"), ("gnd",))
    rc_net("Device:R", "R9", "330R", 396.0, 160.0, ("lbl", "LED_DIN0"), ("lbl", "LED_D1"))
    # 12-LED chain: D1-6 under agent keys, D10-15 under command keys.
    # Better than the original: EVERY key carries status, not just six.
    led = "JLC:SK6812MINI-E_C5149201"
    refs = [f"D{i+1}" for i in range(6)] + [f"D{i+10}" for i in range(6)]
    caps = [f"C{19+i}" for i in range(6)] + [f"C{26+i}" for i in range(6)]
    for i, (ref, cap) in enumerate(zip(refs, caps)):
        lx = 340.0 + (i % 6) * 40.0
        ly = 195.0 if i < 6 else 218.0
        din = f"LED_D{i+1}"
        dout = f"LED_D{i+2}" if i < 11 else None
        spec = {"3": ("pwr", "VBUS"), "1": ("gnd",), "2": ("lbl", din),
                "4": ("lbl", dout) if dout else ("nc",)}
        part_taps(led, ref, "SK6812MINI-E", lx, ly, spec)
        rc_net("Device:C", cap, "100nF", lx + 14.0, ly + 12.0, ("pwr", "VBUS"), ("gnd",))


# ============================================================ SECTION 6
# INPUTS — 12 hotswap keys, EC11, 5-way joystick (all direct to GPIO, GND return)
def section_inputs():
    section_box(330, 240, 580, 360, "INPUTS  (12 choc hotswap + EC11 + 5-way)", 332, 238)
    sock = "JLC:CPG135001S30"
    for n in range(1, 13):
        sx = 345.0 + ((n - 1) % 6) * 40.0
        sy = 260.0 + ((n - 1) // 6) * 25.0
        part_taps(sock, f"SW{n}", f"K{n}", sx, sy, {
            "1": ("lbl", f"K{n}"), "2": ("gnd",),
        })
    enc = "JLC:EC11E1834403"
    part_taps(enc, "ENC1", "EC11", 370.0, 330.0, {
        "A": ("lbl", "ENC_A"), "C": ("gnd",), "B": ("lbl", "ENC_B"),
        "D": ("lbl", "ENC_SW"), "E": ("gnd",),
        "F": ("gnd",), "G": ("gnd",),
    })
    joy = "ClaudeMicro_Custom:SKQUCAA010"
    part_taps(joy, "JS1", "SKQUCAA010", 480.0, 330.0, {
        "1": ("lbl", "JOY_A"), "2": ("lbl", "JOY_B"), "3": ("lbl", "JOY_C"),
        "4": ("gnd",), "5": ("lbl", "JOY_D"), "6": ("lbl", "JOY_CTR"),
    })


# ============================================================ SECTION 7
# TOUCH + AUX LEDS (TTP223 DS: C1 100nF close, Cs DNP NPO, TOG/AHLB float)
def section_touch_aux():
    section_box(26, 340, 320, 410, "TOUCH + AUX LEDS", 28, 338)
    tt = "JLC:TTP223-BA6"
    part_taps(tt, "U5", "TTP223-BA6", 70.0, 370.0, {
        "1": ("lbl", "TOUCH"), "2": ("gnd",), "3": ("lbl", "TOUCH_PAD"),
        "4": ("nc",), "6": ("nc",),          # AHLB/TOG float = direct, active-high
        "5": ("pwr", "+3V3"),
    })
    rc_net("Device:C", "C3", "100nF", 110.0, 365.0, ("pwr", "+3V3"), ("gnd",))
    rc_net("Device:C", "C4", "10pF DNP", 122.0, 365.0, ("lbl", "TOUCH_PAD"), ("gnd",), dnp=True)
    pad = "ClaudeMicro_Custom:TouchPad"
    part_taps(pad, "TP1", "TOUCH_PAD", 40.0, 395.0, {"1": ("lbl", "TOUCH_PAD")})
    led = "JLC:KT-0603R"
    for i in range(3):
        lx = 170.0 + i * 45.0
        rc_net("Device:R", f"R{10+i}", "1k", lx, 370.0, ("lbl", f"AUX{i+1}"), ("lbl", f"AUXK{i+1}"))
        part_taps(led, f"D{7+i}", "red", lx + 18.0, 370.0, {
            "1": ("lbl", f"AUXK{i+1}"), "2": ("gnd",),
        })


# ============================================================ build
section_power()
section_mcu()
section_flash()
section_crystal()
section_leds()
section_inputs()
section_touch_aux()

lib_symbols = '\n'.join('\t\t' + b for b in _blocks.values())
body = '\n'.join(items)
out = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A2")
\t(title_block
\t\t(title "Claude Micro")
\t\t(rev "V0.1")
\t\t(company "Barakaeli Lawuo")
\t\t(comment 1 "Desk controller for Claude Code - RP2040, QMK, per-session RGB")
\t)
\t(lib_symbols
{lib_symbols}
\t)
{body}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''
open("ClaudeMicro.kicad_sch", "w").write(out)
print(f"wrote ClaudeMicro.kicad_sch: {len(out)} bytes, {len(items)} items")

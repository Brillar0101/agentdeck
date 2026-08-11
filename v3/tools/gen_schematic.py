#!/usr/bin/env python3
"""Generate v3/hardware/AgentDeckV3.kicad_sch (and V3.kicad_sym) section by section.

AgentDeck V3 — hand-solderable 24-key AI control deck (ESP32-S3, OLED, LiPo).
Ported from the NeuralCard gen_schematic.py emitter (KiCad 10 S-expressions).
Coordinates: sheet mm, 1.27 grid, y DOWN. Symbols placed at angle 0, no mirror,
so a pin at symbol-local (lx, ly) maps to sheet (px + lx, py - ly).

PINOUT (ESP32-S3-WROOM-1-N8R2, module pin -> GPIO -> net):
  ROW0..ROW3   GPIO4/5/6/7      (p4-p7)    matrix row drives (outputs)
  COL0..COL5   GPIO10..15       (p18,19,20,21,22,8)  matrix column senses
  SDA / SCL    GPIO8 / GPIO9    (p12/p17)  I2C OLED
  USB_DM/DP    GPIO19 / GPIO20  (p13/p14)  native USB (fixed)
  LED_DATA     GPIO21           (p23)      SK6812 chain via U2 AHCT125
  CHRG_SNS     GPIO47           (p24)      TP4056 /CHRG via 10k
  STDBY_SNS    GPIO48           (p25)      TP4056 /STDBY via 10k
  ENC_A/B/SW   GPIO40/41/42     (p33/34/35) EC11
  TOUCH        GPIO1  (T1)      (p39)      native touch pad (touch = GPIO1-14)
  VBAT_SNS     GPIO2  (ADC1_CH1)(p38)      battery divider 100k/47k
  TXD / RXD    GPIO43 / GPIO44  (p37/p36)  UART0 prog pads
  BOOT / EN    GPIO0 (p27) / EN (p3)       tacts; 10k pullups
  Strapping GPIO3(p15)/45(p26)/46(p16) no-connect; PSRAM GPIO35/36/37(p28-30) NC.
  Spare: GPIO16(p9), GPIO17(p10), GPIO18(p11), GPIO38(p31), GPIO39(p32).
"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
V1_HW = os.path.normpath(os.path.join(HERE, "..", "..", "hardware"))
NC = "/Users/barakaeli/Open Source Hardware/NeuralCard"

ROOT_UUID = "c3a1b2d4-0003-4000-8000-000000000003"
PROJECT = "AgentDeckV3"

KSYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
DEVICE_LIB = f"{KSYM}/Device.kicad_sym"
POWER_LIB = f"{KSYM}/power.kicad_sym"
CONN_LIB = f"{KSYM}/Connector_Generic.kicad_sym"
V3_LIB = os.path.join(HW, "V3.kicad_sym")
JLC_V1_LIB = os.path.join(V1_HW, "JLC.kicad_sym")
CUSTOM_LIB = os.path.join(V1_HW, "AgentDeck_Custom.kicad_sym")
NC_JLC_LIB = os.path.join(NC, "JLC.kicad_sym")

# ------------------------------------------------ V3.kicad_sym (project lib)
# Copied from NeuralCard JLC.kicad_sym at generation time:
V3_COPIED = ["ESP32-S3-WROOM-1", "TYPE-C-31-M-12", "USBLC6-2SC6",
             "ME6211C33M5G-N", "AO3401A", "TS-1187A-B-A-B"]

PIN_FMT = ('      (pin passive line (at {x} {y} {rot}) (length 2.54)\n'
           '        (name "{name}" (effects (font (size 1.27 1.27))))\n'
           '        (number "{num}" (effects (font (size 1.27 1.27)))))')


def mini_symbol(name, desc, body_rect, pins):
    """Minimal V3 symbol. pins: (num, name, x, y, rot)."""
    x1, y1, x2, y2 = body_rect
    pin_txt = '\n'.join(PIN_FMT.format(num=n, name=nm, x=x, y=y, rot=r)
                        for n, nm, x, y, r in pins)
    return f'''  (symbol "{name}"
    (pin_names (offset 1.016))
    (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 {y2 + 2.54} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{name}" (at 0 {y1 - 2.54} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Description" "{desc}" (at 0 0 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "{name}_0_1"
      (rectangle (start {x1} {y1}) (end {x2} {y2})
        (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "{name}_1_1"
{pin_txt}
    )
  )'''


MINI_SYMS = [
    mini_symbol("TP4056", "LiPo charger 1A ESOP-8 (docs/datasheets/v3/tp4056.pdf)",
                (-7.62, -7.62, 7.62, 7.62), [
                    ("4", "VCC", -10.16, 5.08, 0),
                    ("8", "CE", -10.16, 2.54, 0),
                    ("1", "TEMP", -10.16, 0, 0),
                    ("2", "PROG", -10.16, -2.54, 0),
                    ("3", "GND", -10.16, -5.08, 0),
                    ("5", "BAT", 10.16, 5.08, 180),
                    ("7", "~{CHRG}", 10.16, 0, 180),
                    ("6", "~{STDBY}", 10.16, -2.54, 180)]),
    mini_symbol("MSK12C02", "SPDT slide power switch, edge mount",
                (-5.08, -5.08, 5.08, 5.08), [
                    ("2", "COM", -7.62, 0, 0),
                    ("1", "A", 7.62, 2.54, 180),
                    ("3", "B", 7.62, -2.54, 180)]),
    mini_symbol("ChocV1", "Kailh Choc V1 key switch, direct solder",
                (-3.81, -2.54, 3.81, 2.54), [
                    ("1", "1", -6.35, 0, 0),
                    ("2", "2", 6.35, 0, 180)]),
    mini_symbol("OLED_HS96L03", "0.96in OLED 128x64 I2C SSD1315 module (C5248080)",
                (-5.08, -6.35, 5.08, 6.35), [
                    ("1", "GND", -7.62, 3.81, 0),
                    ("2", "VCC", -7.62, 1.27, 0),
                    ("3", "SCL", -7.62, -1.27, 0),
                    ("4", "SDA", -7.62, -3.81, 0)]),
]


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


def write_v3_lib():
    blocks = ['  ' + extract_block(NC_JLC_LIB, n) for n in V3_COPIED]
    blocks += MINI_SYMS
    body = '\n'.join(blocks)
    out = (f'(kicad_symbol_lib\n  (version 20241209)\n'
           f'  (generator "gen_schematic_v3")\n  (generator_version "9.0")\n'
           f'{body}\n)\n')
    open(V3_LIB, "w").write(out)
    print(f"wrote {V3_LIB}: {len(out)} bytes")


# ---------------------------------------------------------------- symbol libs
LIBSYMS = {
    "Device:R": (DEVICE_LIB, "R"),
    "Device:C": (DEVICE_LIB, "C"),
    "Device:D": (DEVICE_LIB, "D"),
    "power:GND": (POWER_LIB, "GND"),
    "power:+3V3": (POWER_LIB, "+3V3"),
    "power:VBUS": (POWER_LIB, "VBUS"),
    "power:PWR_FLAG": (POWER_LIB, "PWR_FLAG"),
    "Connector_Generic:Conn_01x02": (CONN_LIB, "Conn_01x02"),
    "V3:ESP32-S3-WROOM-1": (V3_LIB, "ESP32-S3-WROOM-1"),
    "V3:TYPE-C-31-M-12": (V3_LIB, "TYPE-C-31-M-12"),
    "V3:USBLC6-2SC6": (V3_LIB, "USBLC6-2SC6"),
    "V3:ME6211C33M5G-N": (V3_LIB, "ME6211C33M5G-N"),
    "V3:AO3401A": (V3_LIB, "AO3401A"),
    "V3:TS-1187A-B-A-B": (V3_LIB, "TS-1187A-B-A-B"),
    "V3:TP4056": (V3_LIB, "TP4056"),
    "V3:MSK12C02": (V3_LIB, "MSK12C02"),
    "V3:ChocV1": (V3_LIB, "ChocV1"),
    "V3:OLED_HS96L03": (V3_LIB, "OLED_HS96L03"),
    "JLC_V1:SK6812MINI-E_C5149201": (JLC_V1_LIB, "SK6812MINI-E_C5149201"),
    "JLC_V1:SN74AHCT1G125DBVR": (JLC_V1_LIB, "SN74AHCT1G125DBVR"),
    "JLC_V1:EC11E1834403": (JLC_V1_LIB, "EC11E1834403"),
    "AgentDeck_Custom:TouchPad": (CUSTOM_LIB, "TouchPad"),
    "AgentDeck_Custom:ProgPads_1x4": (CUSTOM_LIB, "ProgPads_1x4"),
}

# pin local coords (lx, ly) per lib_id
PIN_XY = {
    "Device:R": {"1": (0, 3.81), "2": (0, -3.81)},
    "Device:C": {"1": (0, 3.81), "2": (0, -3.81)},
    "Device:D": {"1": (-3.81, 0), "2": (3.81, 0)},   # 1=K(left) 2=A(right)
    "Connector_Generic:Conn_01x02": {"1": (-5.08, 0.0), "2": (-5.08, -2.54)},
    "V3:ME6211C33M5G-N": {"1": (-12.70, 2.54), "2": (-12.70, 0.0),
                          "3": (-12.70, -2.54), "4": (12.70, -2.54), "5": (12.70, 2.54)},
    "V3:AO3401A": {"1": (-5.08, 0.0), "2": (2.54, -5.08), "3": (2.54, 5.08)},
    "V3:TS-1187A-B-A-B": {"1": (-5.08, 2.54), "2": (5.08, 2.54),
                          "3": (-5.08, -5.08), "4": (5.08, -5.08)},
    "V3:USBLC6-2SC6": {"1": (-16.51, 7.62), "2": (-16.51, 0.0), "3": (-16.51, -7.62),
                       "4": (16.51, -7.62), "5": (16.51, 0.0), "6": (16.51, 7.62)},
    "V3:TYPE-C-31-M-12": {
        "A1B12": (-6.35, 13.97), "A4B9": (-6.35, 11.43), "B8": (-6.35, 8.89), "A5": (-6.35, 6.35),
        "B7": (-6.35, 3.81), "A6": (-6.35, 1.27), "A7": (-6.35, -1.27), "B6": (-6.35, -3.81),
        "A8": (-6.35, -6.35), "B5": (-6.35, -8.89), "B4A9": (-6.35, -11.43), "B1A12": (-6.35, -13.97),
        "1": (11.43, -13.97), "2": (11.43, -11.43), "3": (11.43, -8.89), "4": (11.43, -6.35)},
    "V3:ESP32-S3-WROOM-1": {
        "1": (-21.59, 10.16), "2": (-21.59, 7.62), "3": (-21.59, 5.08), "4": (-21.59, 2.54),
        "5": (-21.59, 0.0), "6": (-21.59, -2.54), "7": (-21.59, -5.08), "8": (-21.59, -7.62),
        "9": (-21.59, -10.16), "10": (-21.59, -12.70), "11": (-21.59, -15.24), "12": (-21.59, -17.78),
        "13": (-21.59, -20.32), "14": (-21.59, -22.86),
        "15": (-13.97, -35.56), "16": (-11.43, -35.56), "17": (-8.89, -35.56), "18": (-6.35, -35.56),
        "19": (-3.81, -35.56), "20": (-1.27, -35.56), "21": (1.27, -35.56), "22": (3.81, -35.56),
        "23": (6.35, -35.56), "24": (8.89, -35.56), "25": (11.43, -35.56), "26": (13.97, -35.56),
        "27": (21.59, -22.86), "28": (21.59, -20.32), "29": (21.59, -17.78), "30": (21.59, -15.24),
        "31": (21.59, -12.70), "32": (21.59, -10.16), "33": (21.59, -7.62), "34": (21.59, -5.08),
        "35": (21.59, -2.54), "36": (21.59, 0.0), "37": (21.59, 2.54), "38": (21.59, 5.08),
        "39": (21.59, 7.62), "40": (21.59, 10.16), "41": (21.59, 15.24)},
    "V3:TP4056": {"4": (-10.16, 5.08), "8": (-10.16, 2.54), "1": (-10.16, 0.0),
                  "2": (-10.16, -2.54), "3": (-10.16, -5.08),
                  "5": (10.16, 5.08), "7": (10.16, 0.0), "6": (10.16, -2.54)},
    "V3:MSK12C02": {"2": (-7.62, 0.0), "1": (7.62, 2.54), "3": (7.62, -2.54)},
    "V3:ChocV1": {"1": (-6.35, 0.0), "2": (6.35, 0.0)},
    "V3:OLED_HS96L03": {"1": (-7.62, 3.81), "2": (-7.62, 1.27),
                        "3": (-7.62, -1.27), "4": (-7.62, -3.81)},
    "JLC_V1:SK6812MINI-E_C5149201": {"1": (-10.16, 1.27), "2": (-10.16, -1.27),
                                     "3": (10.16, -1.27), "4": (10.16, 1.27)},
    "JLC_V1:SN74AHCT1G125DBVR": {"1": (-8.89, 2.54), "2": (-8.89, 0.0), "3": (-8.89, -2.54),
                                 "4": (8.89, -2.54), "5": (8.89, 2.54)},
    "JLC_V1:EC11E1834403": {"A": (-2.54, -7.62), "B": (2.54, -7.62), "C": (0.0, -7.62),
                            "D": (-2.54, 7.62), "E": (2.54, 7.62),
                            "F": (7.62, 0.0), "G": (-7.62, 0.0)},
    "AgentDeck_Custom:TouchPad": {"1": (0.0, -7.62)},
    "AgentDeck_Custom:ProgPads_1x4": {"1": (-12.7, 3.81), "2": (-12.7, 1.27),
                                        "3": (-12.7, -1.27), "4": (-12.7, -3.81)},
}

# ref -> footprint (lib:fp).  V3:* footprints are drawn in Phase 2.
FP = {
    "U1": "V3:WIRELM-SMD_ESP32-S3-WROOM-1",
    "U2": "JLC_V1:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR",
    "U3": "JLC_V1:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
    "U4": "V3:ESOP-8_TP4056",
    "U5": "JLC_V1:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR",
    "Q1": "Package_TO_SOT_SMD:SOT-23",
    "J1": "JLC_V1:USB-C_SMD-TYPE-C-31-M-12_1",
    "J2": "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    "J3": "AgentDeck:ProgPads_1x4",
    "SW25": "V3:MSK12C02",
    "SW26": "JLC_V1:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
    "SW27": "JLC_V1:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
    "ENC1": "JLC_V1:SW-TH_EC11E1820402",
    "D25": "Diode_SMD:D_SMA",
    "OLED1": "V3:OLED_HS96L03",
    "TP1": "AgentDeck:TouchPad_D12",
}
for _n in range(1, 25):
    FP[f"SW{_n}"] = "V3:ChocV1_Direct"
    FP[f"D{_n}"] = "Diode_SMD:D_SOD-123"
    FP[f"LED{_n}"] = "JLC_V1:LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E"
for _n in range(1, 14):
    FP[f"R{_n}"] = "Resistor_SMD:R_0603_1608Metric"
for _n in range(1, 36):
    FP[f"C{_n}"] = "Capacitor_SMD:C_0603_1608Metric"
for _c in ("C4", "C6", "C7", "C11"):          # bulk 10uF / 1uF on 0805
    FP[_c] = "Capacitor_SMD:C_0805_2012Metric"


def u():
    return str(uuid.uuid4())


def build_lib_symbols():
    blocks = []
    for lib_id, (path, name) in LIBSYMS.items():
        blk = extract_block(path, name)
        blk = blk.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)
        blocks.append('\t\t' + blk)
    return '\n'.join(blocks)


items = []
GRID = 1.27


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


def place(lib_id, ref, value, x, y, angle, pins, props):
    x, y = snap(x), snap(y)
    pin_lines = '\n'.join(f'\t\t(pin "{p}"\n\t\t\t(uuid "{u()}")\n\t\t)' for p in pins)
    props_txt = '\n'.join(props)
    items.append(
        f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {x} {y} {angle})\n\t\t(unit 1)\n'
        f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
        f'\t\t(uuid "{u()}")\n{props_txt}\n{pin_lines}\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def part(lib_id, ref, value, x, y, pins):
    fp = FP.get(ref, "")
    place(lib_id, ref, value, x, y, 0, pins, [
        prop("Reference", ref, x + 2.54, y - 1.27, 0, "left"),
        prop("Value", value, x + 2.54, y + 1.27, 0, "left"),
        prop("Footprint", fp, x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])


def rc(lib_id, ref, value, x, y):
    fp = FP.get(ref, "")
    place(lib_id, ref, value, x, y, 0, ["1", "2"], [
        prop("Reference", ref, x + 1.778, y - 1.016, 0, "left"),
        prop("Value", value, x + 1.778, y + 1.27, 0, "left"),
        prop("Footprint", fp, x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])


PWR_N = [0]
PWR_LIB = {"GND": "power:GND", "+3V3": "power:+3V3", "VBUS": "power:VBUS"}


def pwr(net, x, y):
    PWR_N[0] += 1
    ref = f"#PWR0{PWR_N[0]:03d}"
    vy = y + 3.302 if net == "GND" else y - 3.302
    place(PWR_LIB[net], ref, net, x, y, 0, ["1"], [
        prop("Reference", ref, x, y, 0, hide=True),
        prop("Value", net, x, vy),
        prop("Footprint", "", x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])


FLG_N = [0]


def pwr_flag_at(x, y):
    FLG_N[0] += 1
    ref = f"#FLG0{FLG_N[0]}"
    place("power:PWR_FLAG", ref, "PWR_FLAG", x, y, 0, ["1"], [
        prop("Reference", ref, x, y - 2.54, 0, hide=True),
        prop("Value", "PWR_FLAG", x, y - 2.54, 0),
        prop("Footprint", "", x, y, 0, hide=True),
        prop("Datasheet", "", x, y, 0, hide=True),
        prop("Description", "", x, y, 0, hide=True),
    ])


def tap_dir(spec, x, y, side, length=2.54):
    """spec: ('gnd',) | ('pwr', net) | ('lbl', net) | ('nc',). side: L/R/U/D."""
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
    else:  # lbl
        just = {'L': 'right', 'R': 'left', 'U': 'left', 'D': 'left'}[side]
        glabel(spec[1], ex, ey, 0, just)


def rc_net(lib_id, ref, val, x, y, top_spec, bot_spec):
    rc(lib_id, ref, val, x, y)
    t = ep(x, y, lib_id, "1")
    b = ep(x, y, lib_id, "2")
    tap_dir(top_spec, t[0], t[1], 'U')
    tap_dir(bot_spec, b[0], b[1], 'D')


def diode_net(ref, val, x, y, k_spec, a_spec):
    """Device:D horizontal: pin1 K (left), pin2 A (right)."""
    part("Device:D", ref, val, x, y, ["1", "2"])
    k = ep(x, y, "Device:D", "1")
    a = ep(x, y, "Device:D", "2")
    tap_dir(k_spec, k[0], k[1], 'L')
    tap_dir(a_spec, a[0], a[1], 'R')


def flag_label(net, x, y):
    """PWR_FLAG attached to a global-label net via a short stub."""
    glabel(net, x, y, 0, "left")
    wire(x, y, x, y - 2.54)
    pwr_flag_at(x, y - 2.54)


def sw_btn(ref, x, y, signal):
    """TS-1187A tact: pins A(1),C(3) -> signal (left); B(2),D(4) -> GND (right)."""
    sw = "V3:TS-1187A-B-A-B"
    part(sw, ref, "SW_PUSH", x, y, ["1", "2", "3", "4"])
    for pn, spec, side in (("1", ("lbl", signal), 'L'), ("3", ("lbl", signal), 'L'),
                           ("2", ("gnd",), 'R'), ("4", ("gnd",), 'R')):
        px, py = ep(x, y, sw, pn)
        tap_dir(spec, px, py, side)


# ================================================================ SECTION 1
# POWER — USB-C + ESD, TP4056 charger, AO3401A load share, switch, LDO
def section_power():
    section_box(20, 25, 400, 140,
                "POWER  (USB-C + TP4056 charge + AO3401A load-share + MSK12C02 switch + ME6211 3V3)",
                22, 23)

    # --- USB-C J1 ---
    jx, jy = 45.0, 70.0
    usb = "V3:TYPE-C-31-M-12"
    part(usb, "J1", "TYPE-C-31-M-12", jx, jy,
         ["A1B12", "A4B9", "B8", "A5", "B7", "A6", "A7", "B6", "A8", "B5",
          "B4A9", "B1A12", "1", "2", "3", "4"])
    jspec = {
        "A1B12": ("gnd",), "B1A12": ("gnd",),
        "A4B9": ("pwr", "VBUS"), "B4A9": ("pwr", "VBUS"),
        "A5": ("lbl", "CC1"), "B5": ("lbl", "CC2"),
        "A6": ("lbl", "USB_DP"), "B6": ("lbl", "USB_DP"),
        "A7": ("lbl", "USB_DM"), "B7": ("lbl", "USB_DM"),
        "A8": ("nc",), "B8": ("nc",),
        "1": ("gnd",), "2": ("gnd",), "3": ("gnd",), "4": ("gnd",),
    }
    for pn, spec in jspec.items():
        px, py = ep(jx, jy, usb, pn)
        lx, _ = PIN_XY[usb][pn]
        tap_dir(spec, px, py, 'L' if lx < 0 else 'R')

    # CC 5.1k pulldowns
    rc_net("Device:R", "R1", "5.1k", 75.0, 110.0, ("lbl", "CC1"), ("gnd",))
    rc_net("Device:R", "R2", "5.1k", 88.0, 110.0, ("lbl", "CC2"), ("gnd",))

    # --- USBLC6 ESD clamp U3 (I/O1 = DM on 1&6, I/O2 = DP on 3&4) ---
    ux, uy = 110.0, 40.0
    esd = "V3:USBLC6-2SC6"
    part(esd, "U3", "USBLC6-2SC6", ux, uy, ["1", "2", "3", "4", "5", "6"])
    espec = {"1": ("lbl", "USB_DM"), "2": ("gnd",), "3": ("lbl", "USB_DP"),
             "4": ("lbl", "USB_DP"), "5": ("pwr", "VBUS"), "6": ("lbl", "USB_DM")}
    for pn, spec in espec.items():
        px, py = ep(ux, uy, esd, pn)
        lx, _ = PIN_XY[esd][pn]
        tap_dir(spec, px, py, 'L' if lx < 0 else 'R')

    # --- TP4056 charger U4 ---
    tx, ty = 170.0, 55.0
    tp = "V3:TP4056"
    part(tp, "U4", "TP4056", tx, ty, ["1", "2", "3", "4", "5", "6", "7", "8"])
    tspec = {"4": ("pwr", "VBUS"), "8": ("pwr", "VBUS"), "1": ("gnd",),
             "2": ("lbl", "PROG"), "3": ("gnd",),
             "5": ("lbl", "BAT+"), "7": ("lbl", "CHRG"), "6": ("lbl", "STDBY")}
    for pn, spec in tspec.items():
        px, py = ep(tx, ty, tp, pn)
        lx, _ = PIN_XY[tp][pn]
        tap_dir(spec, px, py, 'L' if lx < 0 else 'R')
    rc_net("Device:R", "R3", "2.4k", 145.0, 110.0, ("lbl", "PROG"), ("gnd",))       # 500 mA
    rc_net("Device:R", "R4", "10k", 200.0, 100.0, ("lbl", "CHRG"), ("lbl", "CHRG_SNS"))
    rc_net("Device:R", "R5", "10k", 213.0, 100.0, ("lbl", "STDBY"), ("lbl", "STDBY_SNS"))
    rc_net("Device:C", "C11", "10uF", 158.0, 110.0, ("pwr", "VBUS"), ("gnd",))      # VCC bulk

    # --- battery connector J2 (JST-PH) ---
    bx, by = 240.0, 110.0
    conn = "Connector_Generic:Conn_01x02"
    part(conn, "J2", "JST-PH-2 LiPo", bx, by, ["1", "2"])
    p1 = ep(bx, by, conn, "1")
    p2 = ep(bx, by, conn, "2")
    tap_dir(("lbl", "BAT+"), p1[0], p1[1], 'L')
    tap_dir(("gnd",), p2[0], p2[1], 'L')

    # --- diode-OR: D25 Schottky VBUS -> VSYS ---
    diode_net("D25", "SS34", 250.0, 40.0, ("lbl", "VSYS"), ("pwr", "VBUS"))

    # --- load share Q1: S=VSYS(bottom), D=BAT+(top), G=VBUS + 100k bleed ---
    qx, qy = 285.0, 55.0
    fet = "V3:AO3401A"
    part(fet, "Q1", "AO3401A", qx, qy, ["1", "2", "3"])
    g = ep(qx, qy, fet, "1")
    s = ep(qx, qy, fet, "2")
    d = ep(qx, qy, fet, "3")
    tap_dir(("pwr", "VBUS"), g[0], g[1], 'L', 5.08)
    tap_dir(("lbl", "VSYS"), s[0], s[1], 'D')
    tap_dir(("lbl", "BAT+"), d[0], d[1], 'U')
    rc_net("Device:R", "R6", "100k", 265.0, 100.0, ("pwr", "VBUS"), ("gnd",))       # gate bleed

    # --- VBAT sense divider 100k/47k + 100nF -> ADC ---
    rc_net("Device:R", "R7", "100k", 310.0, 80.0, ("lbl", "BAT+"), ("lbl", "VBAT_SNS"))
    rc_net("Device:R", "R8", "47k", 310.0, 110.0, ("lbl", "VBAT_SNS"), ("gnd",))
    rc_net("Device:C", "C8", "100nF", 325.0, 110.0, ("lbl", "VBAT_SNS"), ("gnd",))

    # --- power switch SW25: VSYS -> VSYS_SW ---
    sx, sy = 340.0, 40.0
    psw = "V3:MSK12C02"
    part(psw, "SW25", "MSK12C02", sx, sy, ["1", "2", "3"])
    c = ep(sx, sy, psw, "2")
    a = ep(sx, sy, psw, "1")
    b = ep(sx, sy, psw, "3")
    tap_dir(("lbl", "VSYS"), c[0], c[1], 'L')
    tap_dir(("lbl", "VSYS_SW"), a[0], a[1], 'R')
    tap_dir(("nc",), b[0], b[1], 'R')

    # --- LDO U5: VSYS_SW -> 3V3, CE tied high, 1uF in/out ---
    lx, ly = 360.0, 70.0
    ldo = "V3:ME6211C33M5G-N"
    part(ldo, "U5", "ME6211C33", lx, ly, ["1", "2", "3", "4", "5"])
    lspec = {"1": ("lbl", "VSYS_SW"), "2": ("gnd",), "3": ("lbl", "VSYS_SW"),
             "4": ("nc",), "5": ("pwr", "+3V3")}
    for pn, spec in lspec.items():
        px, py = ep(lx, ly, ldo, pn)
        plx, _ = PIN_XY[ldo][pn]
        tap_dir(spec, px, py, 'L' if plx < 0 else 'R')
    rc_net("Device:C", "C6", "1uF", 345.0, 110.0, ("lbl", "VSYS_SW"), ("gnd",))
    rc_net("Device:C", "C7", "1uF", 358.0, 110.0, ("pwr", "+3V3"), ("gnd",))

    # --- PWR_FLAGs: GND / VBUS / +3V3 (power_in nets need a driver) ---
    fy = 33.0
    pwr("GND", 340.36, snap(fy) + 2.54)
    wire(340.36, snap(fy) + 2.54, 340.36, snap(fy))
    pwr_flag_at(340.36, snap(fy))
    pwr("VBUS", 350.52, snap(fy) - 2.54)
    wire(350.52, snap(fy) - 2.54, 350.52, snap(fy))
    pwr_flag_at(350.52, snap(fy))
    pwr("+3V3", 360.68, snap(fy) - 2.54)
    wire(360.68, snap(fy) - 2.54, 360.68, snap(fy))
    pwr_flag_at(360.68, snap(fy))
    # flags on label-driven rails (battery/diode-OR sources are passive pins)
    flag_label("BAT+", 378.46, 45.72)
    flag_label("VSYS", 378.46, 58.42)
    flag_label("VSYS_SW", 378.46, 71.12)


# ================================================================ SECTION 2
# MCU — ESP32-S3-WROOM-1, decoupling, EN/BOOT, prog pads
ESP_SPECS = {
    "1": ("gnd",), "2": ("pwr", "+3V3"), "3": ("lbl", "EN"),
    "4": ("lbl", "ROW0"), "5": ("lbl", "ROW1"), "6": ("lbl", "ROW2"), "7": ("lbl", "ROW3"),
    "8": ("lbl", "COL5"), "9": ("nc",), "10": ("nc",), "11": ("nc",),
    "12": ("lbl", "SDA"), "13": ("lbl", "USB_DM"), "14": ("lbl", "USB_DP"),
    "15": ("nc",),                  # GPIO3 strapping - keep free
    "16": ("nc",),                  # GPIO46 strapping - keep free
    "17": ("lbl", "SCL"),
    "18": ("lbl", "COL0"), "19": ("lbl", "COL1"), "20": ("lbl", "COL2"),
    "21": ("lbl", "COL3"), "22": ("lbl", "COL4"),
    "23": ("lbl", "LED_DATA"), "24": ("lbl", "CHRG_SNS"), "25": ("lbl", "STDBY_SNS"),
    "26": ("nc",),                  # GPIO45 strapping - keep free
    "27": ("lbl", "IO0"),
    "28": ("nc",), "29": ("nc",), "30": ("nc",),   # GPIO35/36/37 PSRAM (N8R2)
    "31": ("nc",), "32": ("nc",),   # GPIO38/39 spare
    "33": ("lbl", "ENC_A"), "34": ("lbl", "ENC_B"), "35": ("lbl", "ENC_SW"),
    "36": ("lbl", "RXD"), "37": ("lbl", "TXD"),
    "38": ("lbl", "VBAT_SNS"), "39": ("lbl", "TOUCH"),
    "40": ("gnd",), "41": ("gnd",),
}


def section_mcu():
    section_box(20, 150, 260, 335, "MCU  (ESP32-S3-WROOM-1-N8R2 + BOOT/RESET + UART prog pads)", 22, 148)

    ux, uy = 140.0, 220.0
    esp = "V3:ESP32-S3-WROOM-1"
    part(esp, "U1", "ESP32-S3-WROOM-1-N8R2", ux, uy, [str(i) for i in range(1, 42)])
    for n in range(1, 42):
        pn = str(n)
        px, py = ep(ux, uy, esp, pn)
        lx, ly = PIN_XY[esp][pn]
        side = 'D' if ly < -30 else ('L' if lx < 0 else 'R')
        tap_dir(ESP_SPECS[pn], px, py, side)

    # decoupling: 3x 100nF + 10uF bulk on +3V3
    for ref, val, cx in [("C1", "100nF", 190.0), ("C2", "100nF", 203.0),
                         ("C3", "100nF", 216.0), ("C4", "10uF", 229.0)]:
        rc_net("Device:C", ref, val, cx, 170.0, ("pwr", "+3V3"), ("gnd",))

    # EN reset per Espressif guidelines: R9 10k pullup + C5 100nF + RESET tact
    rc_net("Device:R", "R9", "10k", 40.0, 180.0, ("pwr", "+3V3"), ("lbl", "EN"))
    rc_net("Device:C", "C5", "100nF", 55.0, 180.0, ("lbl", "EN"), ("gnd",))
    sw_btn("SW27", 45.0, 300.0, "EN")

    # BOOT: R10 10k pullup + BOOT tact on GPIO0
    rc_net("Device:R", "R10", "10k", 70.0, 180.0, ("pwr", "+3V3"), ("lbl", "IO0"))
    sw_btn("SW26", 90.0, 300.0, "IO0")

    # UART prog pads J3 (reuse AgentDeck_Custom ProgPads_1x4):
    # pad1=3V3, pad2=TXD(GPIO43), pad3=GND, pad4=RXD(GPIO44)
    px_, py_ = 200.0, 300.0
    pp = "AgentDeck_Custom:ProgPads_1x4"
    part(pp, "J3", "ProgPads 3V3/TX/GND/RX", px_, py_, ["1", "2", "3", "4"])
    for pn, spec in (("1", ("pwr", "+3V3")), ("2", ("lbl", "TXD")),
                     ("3", ("gnd",)), ("4", ("lbl", "RXD"))):
        cx, cy = ep(px_, py_, pp, pn)
        tap_dir(spec, cx, cy, 'L')


# ================================================================ SECTION 3
# KEY MATRIX — 4 rows x 6 cols, COL2ROW (switch->anode, cathode->row)
def section_matrix():
    section_box(420, 25, 820, 300, "KEY MATRIX  4x6 COL2ROW  (SW pin1=COL, pin2->D anode, D cathode->ROW)", 422, 23)
    for idx in range(24):
        r, c = idx // 6, idx % 6
        x = 445.0 + c * 62.0
        y = 55.0 + r * 62.0
        sw = "V3:ChocV1"
        ref = f"SW{idx + 1}"
        part(sw, ref, "ChocV1", x, y, ["1", "2"])
        p1 = ep(x, y, sw, "1")
        p2 = ep(x, y, sw, "2")
        tap_dir(("lbl", f"COL{c}"), p1[0], p1[1], 'L')
        tap_dir(("lbl", f"KD{idx + 1}"), p2[0], p2[1], 'R')
        diode_net(f"D{idx + 1}", "1N4148W", x + 5.0, y + 15.0,
                  ("lbl", f"ROW{r}"), ("lbl", f"KD{idx + 1}"))


# ================================================================ SECTION 4
# LED CHAIN — SN74AHCT1G125 (VCC=VSYS_SW) + 330R + 24x SK6812MINI-E
def section_leds():
    section_box(20, 345, 820, 560,
                "RGB LEDs  (U2 AHCT125 @VSYS_SW + 330R head + 24x SK6812MINI-E, 100nF each)", 22, 343)

    # buffer U2: A <- LED_DATA (3V3 logic), Y -> LED_DATA_BUF (VSYS_SW logic)
    bx, by = 45.0, 375.0
    buf = "JLC_V1:SN74AHCT1G125DBVR"
    part(buf, "U2", "SN74AHCT1G125", bx, by, ["1", "2", "3", "4", "5"])
    bspec = {"1": ("gnd",), "2": ("lbl", "LED_DATA"), "3": ("gnd",),
             "4": ("lbl", "LED_DATA_BUF"), "5": ("lbl", "VSYS_SW")}
    for pn, spec in bspec.items():
        px, py = ep(bx, by, buf, pn)
        lx, _ = PIN_XY[buf][pn]
        tap_dir(spec, px, py, 'L' if lx < 0 else 'R')
    rc_net("Device:C", "C9", "100nF", 70.0, 375.0, ("lbl", "VSYS_SW"), ("gnd",))
    rc_net("Device:R", "R11", "330R", 85.0, 375.0, ("lbl", "LED_DATA_BUF"), ("lbl", "LED_D1"))

    led = "JLC_V1:SK6812MINI-E_C5149201"
    for idx in range(24):
        r, c = idx // 8, idx % 8
        x = 130.0 + c * 88.0
        y = 390.0 + r * 58.0
        ref = f"LED{idx + 1}"
        part(led, ref, "SK6812MINI-E", x, y, ["1", "2", "3", "4"])
        gnd_p = ep(x, y, led, "1")
        din = ep(x, y, led, "2")
        vdd = ep(x, y, led, "3")
        dout = ep(x, y, led, "4")
        tap_dir(("gnd",), gnd_p[0], gnd_p[1], 'L', 5.08)
        tap_dir(("lbl", f"LED_D{idx + 1}"), din[0], din[1], 'L')
        tap_dir(("lbl", "VSYS_SW"), vdd[0], vdd[1], 'R')
        if idx < 23:
            tap_dir(("lbl", f"LED_D{idx + 2}"), dout[0], dout[1], 'R', 5.08)
        else:
            tap_dir(("nc",), dout[0], dout[1], 'R')
        rc_net("Device:C", f"C{12 + idx}", "100nF", x + 5.0, y + 17.78,
               ("lbl", "VSYS_SW"), ("gnd",))


# ================================================================ SECTION 5
# PERIPHERALS — OLED I2C, touch pad, EC11 encoder
def section_periph():
    section_box(270, 150, 410, 335, "PERIPHERALS  (OLED I2C + touch pad + EC11)", 272, 148)

    # OLED module
    ox, oy = 330.0, 180.0
    oled = "V3:OLED_HS96L03"
    part(oled, "OLED1", "HS96L03W2C03", ox, oy, ["1", "2", "3", "4"])
    for pn, spec in (("1", ("gnd",)), ("2", ("pwr", "+3V3")),
                     ("3", ("lbl", "SCL")), ("4", ("lbl", "SDA"))):
        px, py = ep(ox, oy, oled, pn)
        tap_dir(spec, px, py, 'L')
    # I2C pullups + OLED decoupling
    rc_net("Device:R", "R12", "4.7k", 360.0, 180.0, ("pwr", "+3V3"), ("lbl", "SDA"))
    rc_net("Device:R", "R13", "4.7k", 373.0, 180.0, ("pwr", "+3V3"), ("lbl", "SCL"))
    rc_net("Device:C", "C10", "100nF", 388.0, 180.0, ("pwr", "+3V3"), ("gnd",))

    # touch pad (ESP32-S3 native touch, GPIO1/T1)
    tx, ty = 390.0, 240.0
    tp = "AgentDeck_Custom:TouchPad"
    part(tp, "TP1", "TouchPad", tx, ty, ["1"])
    px, py = ep(tx, ty, tp, "1")
    tap_dir(("lbl", "TOUCH"), px, py, 'D')

    # EC11 encoder: A/B/SW to GPIOs, common + switch-common + frame to GND
    ex, ey = 320.0, 260.0
    enc = "JLC_V1:EC11E1834403"
    part(enc, "ENC1", "EC11", ex, ey, ["A", "B", "C", "D", "E", "F", "G"])
    espec = {"A": (("lbl", "ENC_A"), 'D', 5.08), "B": (("lbl", "ENC_B"), 'D', 7.62),
             "C": (("gnd",), 'D', 2.54),
             "D": (("lbl", "ENC_SW"), 'U', 2.54), "E": (("gnd",), 'U', 2.54),
             "F": (("gnd",), 'R', 2.54), "G": (("gnd",), 'L', 2.54)}
    for pn, (spec, side, ln) in espec.items():
        px, py = ep(ex, ey, enc, pn)
        tap_dir(spec, px, py, side, ln)


# ================================================================ build
def print_pinout():
    print(__doc__.split("PINOUT", 1)[1].split('"""')[0]
          if False else "PINOUT: see module docstring")
    for line in __doc__.splitlines():
        if line.startswith("  "):
            print(line)


write_v3_lib()
section_power()
section_mcu()
section_matrix()
section_leds()
section_periph()

lib_symbols = build_lib_symbols()
body = '\n'.join(items)
out = f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A1")
\t(title_block
\t\t(title "AgentDeckV3")
\t\t(rev "V0.1")
\t\t(company "Barakaeli Lawuo")
\t\t(comment 1 "Hand-solderable AI control deck - 24 keys, OLED, touch, LiPo, ESP32-S3")
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
sch_path = os.path.join(HW, "AgentDeckV3.kicad_sch")
open(sch_path, "w").write(out)
print(f"wrote {sch_path}: {len(out)} bytes, {len(items)} items")
print_pinout()

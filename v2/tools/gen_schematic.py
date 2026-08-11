#!/usr/bin/env python3
"""Generate v2/hardware/AgentDeckV2.kicad_sch (and V2.kicad_sym) section by section.

AgentDeck V2 — wireless 20-key deck with status LCD (ESP32-S3, BLE+USB, LiPo).
Ported from the V3 emitter (KiCad 10 S-expressions). Coordinates: sheet mm,
1.27 grid, y DOWN. Symbols at angle 0, no mirror: a pin at symbol-local
(lx, ly) maps to sheet (px + lx, py - ly).

PINOUT (ESP32-S3-WROOM-1-N8R2, module pin -> GPIO -> net):
  ROW0..ROW3   GPIO4/5/6/7      (p4-p7)   matrix row drives (keys)
  ROW4         GPIO15           (p8)      joystick COM row
  COL0..COL4   GPIO10..14       (p18-p22) matrix column senses
  LCD_MOSI     GPIO8            (p12)     ST7789V SDA
  LCD_SCK      GPIO9            (p17)     ST7789V SCL
  LCD_DC       GPIO16           (p9)      ST7789V RS
  LCD_CS       GPIO17           (p10)
  LCD_RST      GPIO18           (p11)
  LCD_BL       GPIO1            (p39)     backlight PWM via Q2 AO3400A
  USB_DM/DP    GPIO19 / GPIO20  (p13/p14) native USB (fixed)
  LED_DATA     GPIO21           (p23)     SK6812 x20 via U2 AHCT125
  CHRG_SNS     GPIO47           (p24)     TP4056 /CHRG via 10k
  STDBY_SNS    GPIO48           (p25)     TP4056 /STDBY via 10k
  ENC_A/B/SW   GPIO40/41/42     (p33/34/35) EC11
  VBAT_SNS     GPIO2  (ADC1_CH1)(p38)     battery divider 100k/47k
  TXD / RXD    GPIO43 / GPIO44  (p37/p36) UART0 prog pads
  BOOT / EN    GPIO0 (p27) / EN (p3)      tacts; 10k pullups
  Strapping GPIO3(p15)/45(p26)/46(p16) no-connect; PSRAM GPIO35/36/37(p28-30) NC.
  Spare: GPIO38(p31), GPIO39(p32).

MATRIX: 5 rows x 5 cols COL2ROW. SW1-20 fill rows 0-3. The SKQUCAA010
joystick is row 4: its five switches share COM (-> ROW4); each direction pin
enters through its own 1N4148W from a column (anode at column, cathode at
the direction pin), preserving one diode per switch and matrix polarity.
"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
V1_HW = os.path.normpath(os.path.join(HERE, "..", "..", "v1", "hardware"))
V3_HW = os.path.normpath(os.path.join(HERE, "..", "..", "v3", "hardware"))

ROOT_UUID = "c3a1b2d4-0002-4000-8000-000000000002"
PROJECT = "AgentDeckV2"

KSYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
DEVICE_LIB = f"{KSYM}/Device.kicad_sym"
POWER_LIB = f"{KSYM}/power.kicad_sym"
CONN_LIB = f"{KSYM}/Connector_Generic.kicad_sym"
V2_LIB = os.path.join(HW, "V2.kicad_sym")
V2_JLC_LIB = os.path.join(HW, "JLC.kicad_sym")
V3_SRC_LIB = os.path.join(V3_HW, "V3.kicad_sym")
JLC_V1_LIB = os.path.join(V1_HW, "JLC.kicad_sym")
CUSTOM_LIB = os.path.join(V1_HW, "AgentDeck_Custom.kicad_sym")

# Symbols copied into V2.kicad_sym at generation time.
V2_FROM_V3 = ["ESP32-S3-WROOM-1", "TYPE-C-31-M-12", "USBLC6-2SC6",
              "ME6211C33M5G-N", "AO3401A", "TS-1187A-B-A-B", "TP4056",
              "MSK12C02", "ChocV1"]
V2_FROM_JLC = ["N114-2413THBIG01-H13", "AO3400A"]


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


def write_v2_lib():
    blocks = ['  ' + extract_block(V3_SRC_LIB, n) for n in V2_FROM_V3]
    blocks += ['  ' + extract_block(V2_JLC_LIB, n) for n in V2_FROM_JLC]
    body = '\n'.join(blocks)
    out = (f'(kicad_symbol_lib\n  (version 20241209)\n'
           f'  (generator "gen_schematic_v2")\n  (generator_version "9.0")\n'
           f'{body}\n)\n')
    open(V2_LIB, "w").write(out)
    print(f"wrote {V2_LIB}: {len(out)} bytes")


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
    "V2:ESP32-S3-WROOM-1": (V2_LIB, "ESP32-S3-WROOM-1"),
    "V2:TYPE-C-31-M-12": (V2_LIB, "TYPE-C-31-M-12"),
    "V2:USBLC6-2SC6": (V2_LIB, "USBLC6-2SC6"),
    "V2:ME6211C33M5G-N": (V2_LIB, "ME6211C33M5G-N"),
    "V2:AO3401A": (V2_LIB, "AO3401A"),
    "V2:AO3400A": (V2_LIB, "AO3400A"),
    "V2:TS-1187A-B-A-B": (V2_LIB, "TS-1187A-B-A-B"),
    "V2:TP4056": (V2_LIB, "TP4056"),
    "V2:MSK12C02": (V2_LIB, "MSK12C02"),
    "V2:ChocV1": (V2_LIB, "ChocV1"),
    "V2:N114-2413THBIG01-H13": (V2_LIB, "N114-2413THBIG01-H13"),
    "JLC_V1:SK6812MINI-E_C5149201": (JLC_V1_LIB, "SK6812MINI-E_C5149201"),
    "JLC_V1:SN74AHCT1G125DBVR": (JLC_V1_LIB, "SN74AHCT1G125DBVR"),
    "JLC_V1:EC11E1834403": (JLC_V1_LIB, "EC11E1834403"),
    "AgentDeck_Custom:SKQUCAA010": (CUSTOM_LIB, "SKQUCAA010"),
    "AgentDeck_Custom:ProgPads_1x4": (CUSTOM_LIB, "ProgPads_1x4"),
}

# pin local coords (lx, ly) per lib_id
PIN_XY = {
    "Device:R": {"1": (0, 3.81), "2": (0, -3.81)},
    "Device:C": {"1": (0, 3.81), "2": (0, -3.81)},
    "Device:D": {"1": (-3.81, 0), "2": (3.81, 0)},   # 1=K(left) 2=A(right)
    "Connector_Generic:Conn_01x02": {"1": (-5.08, 0.0), "2": (-5.08, -2.54)},
    "V2:ME6211C33M5G-N": {"1": (-12.70, 2.54), "2": (-12.70, 0.0),
                          "3": (-12.70, -2.54), "4": (12.70, -2.54), "5": (12.70, 2.54)},
    "V2:AO3401A": {"1": (-5.08, 0.0), "2": (2.54, -5.08), "3": (2.54, 5.08)},
    "V2:AO3400A": {"1": (-5.08, 0.0), "2": (2.54, -5.08), "3": (2.54, 5.08)},
    "V2:TS-1187A-B-A-B": {"1": (-5.08, 2.54), "2": (5.08, 2.54),
                          "3": (-5.08, -5.08), "4": (5.08, -5.08)},
    "V2:USBLC6-2SC6": {"1": (-16.51, 7.62), "2": (-16.51, 0.0), "3": (-16.51, -7.62),
                       "4": (16.51, -7.62), "5": (16.51, 0.0), "6": (16.51, 7.62)},
    "V2:TYPE-C-31-M-12": {
        "A1B12": (-6.35, 13.97), "A4B9": (-6.35, 11.43), "B8": (-6.35, 8.89), "A5": (-6.35, 6.35),
        "B7": (-6.35, 3.81), "A6": (-6.35, 1.27), "A7": (-6.35, -1.27), "B6": (-6.35, -3.81),
        "A8": (-6.35, -6.35), "B5": (-6.35, -8.89), "B4A9": (-6.35, -11.43), "B1A12": (-6.35, -13.97),
        "1": (11.43, -13.97), "2": (11.43, -11.43), "3": (11.43, -8.89), "4": (11.43, -6.35)},
    "V2:ESP32-S3-WROOM-1": {
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
    "V2:TP4056": {"4": (-10.16, 5.08), "8": (-10.16, 2.54), "1": (-10.16, 0.0),
                  "2": (-10.16, -2.54), "3": (-10.16, -5.08),
                  "5": (10.16, 5.08), "7": (10.16, 0.0), "6": (10.16, -2.54)},
    "V2:MSK12C02": {"2": (-7.62, 0.0), "1": (7.62, 2.54), "3": (7.62, -2.54)},
    "V2:ChocV1": {"1": (-6.35, 0.0), "2": (6.35, 0.0)},
    "V2:N114-2413THBIG01-H13": {
        "1": (-6.35, 15.24), "2": (-6.35, 12.70), "3": (-6.35, 10.16), "4": (-6.35, 7.62),
        "5": (-6.35, 5.08), "6": (-6.35, 2.54), "7": (-6.35, 0.0), "8": (-6.35, -2.54),
        "9": (-6.35, -5.08), "10": (-6.35, -7.62), "11": (-6.35, -10.16),
        "12": (-6.35, -12.70), "13": (-6.35, -15.24)},
    "JLC_V1:SK6812MINI-E_C5149201": {"1": (-10.16, 1.27), "2": (-10.16, -1.27),
                                     "3": (10.16, -1.27), "4": (10.16, 1.27)},
    "JLC_V1:SN74AHCT1G125DBVR": {"1": (-8.89, 2.54), "2": (-8.89, 0.0), "3": (-8.89, -2.54),
                                 "4": (8.89, -2.54), "5": (8.89, 2.54)},
    "JLC_V1:EC11E1834403": {"A": (-2.54, -7.62), "B": (2.54, -7.62), "C": (0.0, -7.62),
                            "D": (-2.54, 7.62), "E": (2.54, 7.62),
                            "F": (7.62, 0.0), "G": (-7.62, 0.0)},
    "AgentDeck_Custom:SKQUCAA010": {"1": (-12.7, 5.08), "2": (-12.7, 0.0), "3": (-12.7, -5.08),
                                    "4": (12.7, -5.08), "5": (12.7, 0.0), "6": (12.7, 5.08)},
    "AgentDeck_Custom:ProgPads_1x4": {"1": (-12.7, 3.81), "2": (-12.7, 1.27),
                                      "3": (-12.7, -1.27), "4": (-12.7, -3.81)},
}

# ref -> footprint (lib:fp)
FP = {
    "U1": "JLC:WIRELM-SMD_ESP32-S3-WROOM-1",
    "U2": "JLC_V1:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR",
    "U3": "JLC:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
    "U4": "JLC:ESOP-8_L4.9-W3.9-P1.27-LS6.0-BL-EP",
    "U5": "JLC_V1:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR",
    "Q1": "Package_TO_SOT_SMD:SOT-23",
    "Q2": "JLC:SOT-23-3P_L2.9-W1.3-H1.0-LS2.4-P0.95",
    "J1": "JLC:USB-C_SMD-TYPE-C-31-M-12_1",
    "J2": "JLC:CONN-SMD_P2.00_S2B-PH-SM4-TB-LF-SN",
    "J3": "AgentDeck:ProgPads_1x4",
    "JS1": "AgentDeck:SKQUCAA010",
    "SW25": "V3:MSK12C02",
    "SW26": "JLC_V1:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
    "SW27": "JLC_V1:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
    "ENC1": "JLC_V1:SW-TH_EC11E1820402",
    "D26": "Diode_SMD:D_SMA",
    "LCD1": "JLC:LCD-SMD_1.14IPS-LCD",
}
for _n in range(1, 21):
    FP[f"SW{_n}"] = "JLC_V1:CONN-SMD_HOTPLUGPAKAGE__C9900010116"
    FP[f"LED{_n}"] = "JLC_V1:LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E"
for _n in range(1, 26):
    FP[f"D{_n}"] = "Diode_SMD:D_SOD-123"
for _n in range(1, 16):
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
    glabel(net, x, y, 0, "left")
    wire(x, y, x, y - 2.54)
    pwr_flag_at(x, y - 2.54)


def sw_btn(ref, x, y, signal):
    """TS-1187A tact: pins A(1),C(3) -> signal (left); B(2),D(4) -> GND (right)."""
    sw = "V2:TS-1187A-B-A-B"
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

    jx, jy = 45.0, 70.0
    usb = "V2:TYPE-C-31-M-12"
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

    rc_net("Device:R", "R1", "5.1k", 75.0, 110.0, ("lbl", "CC1"), ("gnd",))
    rc_net("Device:R", "R2", "5.1k", 88.0, 110.0, ("lbl", "CC2"), ("gnd",))

    ux, uy = 110.0, 40.0
    esd = "V2:USBLC6-2SC6"
    part(esd, "U3", "USBLC6-2SC6", ux, uy, ["1", "2", "3", "4", "5", "6"])
    espec = {"1": ("lbl", "USB_DM"), "2": ("gnd",), "3": ("lbl", "USB_DP"),
             "4": ("lbl", "USB_DP"), "5": ("pwr", "VBUS"), "6": ("lbl", "USB_DM")}
    for pn, spec in espec.items():
        px, py = ep(ux, uy, esd, pn)
        lx, _ = PIN_XY[esd][pn]
        tap_dir(spec, px, py, 'L' if lx < 0 else 'R')

    tx, ty = 170.0, 55.0
    tp = "V2:TP4056"
    part(tp, "U4", "TP4056", tx, ty, ["1", "2", "3", "4", "5", "6", "7", "8"])
    tspec = {"4": ("pwr", "VBUS"), "8": ("pwr", "VBUS"), "1": ("gnd",),
             "2": ("lbl", "PROG"), "3": ("gnd",),
             "5": ("lbl", "BAT+"), "7": ("lbl", "CHRG"), "6": ("lbl", "STDBY")}
    for pn, spec in tspec.items():
        px, py = ep(tx, ty, tp, pn)
        lx, _ = PIN_XY[tp][pn]
        tap_dir(spec, px, py, 'L' if lx < 0 else 'R')
    rc_net("Device:R", "R3", "1.2k", 145.0, 110.0, ("lbl", "PROG"), ("gnd",))       # 1 A for 2000mAh cell
    rc_net("Device:R", "R4", "10k", 200.0, 100.0, ("lbl", "CHRG"), ("lbl", "CHRG_SNS"))
    rc_net("Device:R", "R5", "10k", 213.0, 100.0, ("lbl", "STDBY"), ("lbl", "STDBY_SNS"))
    rc_net("Device:C", "C11", "10uF", 158.0, 110.0, ("pwr", "VBUS"), ("gnd",))

    bx, by = 240.0, 110.0
    conn = "Connector_Generic:Conn_01x02"
    part(conn, "J2", "JST-PH-2 LiPo", bx, by, ["1", "2"])
    p1 = ep(bx, by, conn, "1")
    p2 = ep(bx, by, conn, "2")
    tap_dir(("lbl", "BAT+"), p1[0], p1[1], 'L')
    tap_dir(("gnd",), p2[0], p2[1], 'L')

    diode_net("D26", "SS34", 250.0, 40.0, ("lbl", "VSYS"), ("pwr", "VBUS"))

    qx, qy = 285.0, 55.0
    fet = "V2:AO3401A"
    part(fet, "Q1", "AO3401A", qx, qy, ["1", "2", "3"])
    g = ep(qx, qy, fet, "1")
    s = ep(qx, qy, fet, "2")
    d = ep(qx, qy, fet, "3")
    tap_dir(("pwr", "VBUS"), g[0], g[1], 'L', 5.08)
    tap_dir(("lbl", "VSYS"), s[0], s[1], 'D')
    tap_dir(("lbl", "BAT+"), d[0], d[1], 'U')
    rc_net("Device:R", "R6", "100k", 265.0, 100.0, ("pwr", "VBUS"), ("gnd",))

    rc_net("Device:R", "R7", "100k", 310.0, 80.0, ("lbl", "BAT+"), ("lbl", "VBAT_SNS"))
    rc_net("Device:R", "R8", "47k", 310.0, 110.0, ("lbl", "VBAT_SNS"), ("gnd",))
    rc_net("Device:C", "C8", "100nF", 325.0, 110.0, ("lbl", "VBAT_SNS"), ("gnd",))

    sx, sy = 340.0, 40.0
    psw = "V2:MSK12C02"
    part(psw, "SW25", "MSK12C02", sx, sy, ["1", "2", "3"])
    c = ep(sx, sy, psw, "2")
    a = ep(sx, sy, psw, "1")
    b = ep(sx, sy, psw, "3")
    tap_dir(("lbl", "VSYS"), c[0], c[1], 'L')
    tap_dir(("lbl", "VSYS_SW"), a[0], a[1], 'R')
    tap_dir(("nc",), b[0], b[1], 'R')

    lx, ly = 360.0, 70.0
    ldo = "V2:ME6211C33M5G-N"
    part(ldo, "U5", "ME6211C33", lx, ly, ["1", "2", "3", "4", "5"])
    lspec = {"1": ("lbl", "VSYS_SW"), "2": ("gnd",), "3": ("lbl", "VSYS_SW"),
             "4": ("nc",), "5": ("pwr", "+3V3")}
    for pn, spec in lspec.items():
        px, py = ep(lx, ly, ldo, pn)
        plx, _ = PIN_XY[ldo][pn]
        tap_dir(spec, px, py, 'L' if plx < 0 else 'R')
    rc_net("Device:C", "C6", "1uF", 345.0, 110.0, ("lbl", "VSYS_SW"), ("gnd",))
    rc_net("Device:C", "C7", "1uF", 358.0, 110.0, ("pwr", "+3V3"), ("gnd",))

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
    flag_label("BAT+", 378.46, 45.72)
    flag_label("VSYS", 378.46, 58.42)
    flag_label("VSYS_SW", 378.46, 71.12)


# ================================================================ SECTION 2
# MCU — ESP32-S3-WROOM-1, decoupling, EN/BOOT, prog pads
ESP_SPECS = {
    "1": ("gnd",), "2": ("pwr", "+3V3"), "3": ("lbl", "EN"),
    "4": ("lbl", "ROW0"), "5": ("lbl", "ROW1"), "6": ("lbl", "ROW2"), "7": ("lbl", "ROW3"),
    "8": ("lbl", "ROW4"),
    "9": ("lbl", "LCD_DC"), "10": ("lbl", "LCD_CS"), "11": ("lbl", "LCD_RST"),
    "12": ("lbl", "LCD_MOSI"), "13": ("lbl", "USB_DM"), "14": ("lbl", "USB_DP"),
    "15": ("nc",),                  # GPIO3 strapping - keep free
    "16": ("nc",),                  # GPIO46 strapping - keep free
    "17": ("lbl", "LCD_SCK"),
    "18": ("lbl", "COL0"), "19": ("lbl", "COL1"), "20": ("lbl", "COL2"),
    "21": ("lbl", "COL3"), "22": ("lbl", "COL4"),
    "23": ("lbl", "LED_DATA"), "24": ("lbl", "CHRG_SNS"), "25": ("lbl", "STDBY_SNS"),
    "26": ("nc",),                  # GPIO45 strapping - keep free
    "27": ("lbl", "IO0"),
    "28": ("nc",), "29": ("nc",), "30": ("nc",),   # GPIO35/36/37 PSRAM (N8R2)
    "31": ("nc",), "32": ("nc",),   # GPIO38/39 spare
    "33": ("lbl", "ENC_A"), "34": ("lbl", "ENC_B"), "35": ("lbl", "ENC_SW"),
    "36": ("lbl", "RXD"), "37": ("lbl", "TXD"),
    "38": ("lbl", "VBAT_SNS"), "39": ("lbl", "LCD_BL"),
    "40": ("gnd",), "41": ("gnd",),
}


def section_mcu():
    section_box(20, 150, 260, 335, "MCU  (ESP32-S3-WROOM-1-N8R2 + BOOT/RESET + UART prog pads)", 22, 148)

    ux, uy = 140.0, 220.0
    esp = "V2:ESP32-S3-WROOM-1"
    part(esp, "U1", "ESP32-S3-WROOM-1-N8R2", ux, uy, [str(i) for i in range(1, 42)])
    for n in range(1, 42):
        pn = str(n)
        px, py = ep(ux, uy, esp, pn)
        lx, ly = PIN_XY[esp][pn]
        side = 'D' if ly < -30 else ('L' if lx < 0 else 'R')
        tap_dir(ESP_SPECS[pn], px, py, side)

    for ref, val, cx in [("C1", "100nF", 190.0), ("C2", "100nF", 203.0),
                         ("C3", "100nF", 216.0), ("C4", "10uF", 229.0)]:
        rc_net("Device:C", ref, val, cx, 170.0, ("pwr", "+3V3"), ("gnd",))

    rc_net("Device:R", "R9", "10k", 40.0, 180.0, ("pwr", "+3V3"), ("lbl", "EN"))
    rc_net("Device:C", "C5", "100nF", 55.0, 180.0, ("lbl", "EN"), ("gnd",))
    sw_btn("SW27", 45.0, 300.0, "EN")

    rc_net("Device:R", "R10", "10k", 70.0, 180.0, ("pwr", "+3V3"), ("lbl", "IO0"))
    sw_btn("SW26", 90.0, 300.0, "IO0")

    px_, py_ = 200.0, 300.0
    pp = "AgentDeck_Custom:ProgPads_1x4"
    part(pp, "J3", "ProgPads 3V3/TX/GND/RX", px_, py_, ["1", "2", "3", "4"])
    for pn, spec in (("1", ("pwr", "+3V3")), ("2", ("lbl", "TXD")),
                     ("3", ("gnd",)), ("4", ("lbl", "RXD"))):
        cx, cy = ep(px_, py_, pp, pn)
        tap_dir(spec, cx, cy, 'L')


# ================================================================ SECTION 3
# KEY MATRIX — 5 rows x 5 cols COL2ROW; rows 0-3 = SW1-20, row 4 = joystick
def section_matrix():
    section_box(420, 25, 790, 300,
                "KEY MATRIX  5x5 COL2ROW  (SW pin1=COL, pin2->D anode, D cathode->ROW; JS on ROW4)",
                422, 23)
    for idx in range(20):
        r, c = idx // 5, idx % 5
        x = 445.0 + c * 68.0
        y = 55.0 + r * 55.0
        sw = "V2:ChocV1"
        ref = f"SW{idx + 1}"
        part(sw, ref, "ChocV1", x, y, ["1", "2"])
        p1 = ep(x, y, sw, "1")
        p2 = ep(x, y, sw, "2")
        tap_dir(("lbl", f"COL{c}"), p1[0], p1[1], 'L')
        tap_dir(("lbl", f"KD{idx + 1}"), p2[0], p2[1], 'R')
        diode_net(f"D{idx + 1}", "1N4148W", x + 5.0, y + 15.0,
                  ("lbl", f"ROW{r}"), ("lbl", f"KD{idx + 1}"))

    # joystick row: COLc -> D anode, D cathode -> direction pin; COM -> ROW4
    jx, jy = 520.0, 275.0
    js = "AgentDeck_Custom:SKQUCAA010"
    part(js, "JS1", "SKQUCAA010", jx, jy, ["1", "2", "3", "4", "5", "6"])
    jmap = {"1": "JS_UP", "2": "JS_LEFT", "3": "JS_DOWN", "5": "JS_RIGHT", "6": "JS_CTR"}
    for pn, net in jmap.items():
        px, py = ep(jx, jy, js, pn)
        lx, _ = PIN_XY[js][pn]
        tap_dir(("lbl", net), px, py, 'L' if lx < 0 else 'R')
    com = ep(jx, jy, js, "4")
    tap_dir(("lbl", "ROW4"), com[0], com[1], 'R')
    for i, (net, col) in enumerate([("JS_UP", 0), ("JS_LEFT", 1), ("JS_DOWN", 2),
                                    ("JS_RIGHT", 3), ("JS_CTR", 4)]):
        diode_net(f"D{21 + i}", "1N4148W", 620.0 + (i % 3) * 55.0, 262.0 + (i // 3) * 22.0,
                  ("lbl", net), ("lbl", f"COL{col}"))


# ================================================================ SECTION 4
# LED CHAIN — SN74AHCT1G125 (VCC=VSYS_SW) + 330R + 20x SK6812MINI-E
def section_leds():
    section_box(20, 345, 790, 545,
                "RGB LEDs  (U2 AHCT125 @VSYS_SW + 330R head + 20x SK6812MINI-E, 100nF each)", 22, 343)

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
    for idx in range(20):
        r, c = idx // 7, idx % 7
        x = 130.0 + c * 92.0
        y = 390.0 + r * 55.0
        ref = f"LED{idx + 1}"
        part(led, ref, "SK6812MINI-E", x, y, ["1", "2", "3", "4"])
        gnd_p = ep(x, y, led, "1")
        din = ep(x, y, led, "2")
        vdd = ep(x, y, led, "3")
        dout = ep(x, y, led, "4")
        tap_dir(("gnd",), gnd_p[0], gnd_p[1], 'L', 5.08)
        tap_dir(("lbl", f"LED_D{idx + 1}"), din[0], din[1], 'L')
        tap_dir(("lbl", "VSYS_SW"), vdd[0], vdd[1], 'R')
        if idx < 19:
            tap_dir(("lbl", f"LED_D{idx + 2}"), dout[0], dout[1], 'R', 5.08)
        else:
            tap_dir(("nc",), dout[0], dout[1], 'R')
        rc_net("Device:C", f"C{12 + idx}", "100nF", x + 5.0, y + 17.78,
               ("lbl", "VSYS_SW"), ("gnd",))


# ================================================================ SECTION 5
# PERIPHERALS — ST7789V SPI LCD + backlight FET, EC11 encoder
def section_periph():
    section_box(270, 150, 410, 335, "PERIPHERALS  (1.14in ST7789V SPI LCD + EC11)", 272, 148)

    ox, oy = 330.0, 195.0
    lcd = "V2:N114-2413THBIG01-H13"
    part(lcd, "LCD1", "N114-2413THBIG01-H13", ox, oy,
         [str(i) for i in range(1, 14)])
    lspec = {
        "1": ("nc",), "2": ("nc",), "9": ("nc",),
        "3": ("lbl", "LCD_MOSI"), "4": ("lbl", "LCD_SCK"), "5": ("lbl", "LCD_DC"),
        "6": ("lbl", "LCD_RST"), "7": ("lbl", "LCD_CS"),
        "8": ("gnd",), "13": ("gnd",),
        "10": ("pwr", "+3V3"),
        "11": ("lbl", "LCD_LEDK"), "12": ("lbl", "LCD_LEDA"),
    }
    for pn, spec in lspec.items():
        px, py = ep(ox, oy, lcd, pn)
        tap_dir(spec, px, py, 'L')
    rc_net("Device:C", "C10", "100nF", 388.0, 180.0, ("pwr", "+3V3"), ("gnd",))
    # backlight: +3V3 -> R12 -> LEDA ... LEDK -> Q2 drain; Q2 gate = LCD_BL PWM
    rc_net("Device:R", "R12", "22R", 360.0, 180.0, ("pwr", "+3V3"), ("lbl", "LCD_LEDA"))
    qx, qy = 375.0, 240.0
    nfet = "V2:AO3400A"
    part(nfet, "Q2", "AO3400A", qx, qy, ["1", "2", "3"])
    g = ep(qx, qy, nfet, "1")
    s = ep(qx, qy, nfet, "2")
    d = ep(qx, qy, nfet, "3")
    tap_dir(("lbl", "LCD_BL"), g[0], g[1], 'L', 5.08)
    tap_dir(("gnd",), s[0], s[1], 'D')
    tap_dir(("lbl", "LCD_LEDK"), d[0], d[1], 'U')
    rc_net("Device:R", "R13", "10k", 352.0, 290.0, ("lbl", "LCD_BL"), ("gnd",))

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
write_v2_lib()
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
\t\t(title "AgentDeckV2")
\t\t(rev "V0.1")
\t\t(company "Barakaeli Lawuo")
\t\t(comment 1 "Wireless 20-key AI control deck - LCD, LiPo, BLE+USB, ESP32-S3")
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
sch_path = os.path.join(HW, "AgentDeckV2.kicad_sch")
open(sch_path, "w").write(out)
print(f"wrote {sch_path}: {len(out)} bytes, {len(items)} items")

# AgentDeck V3: Hand-Solderable AI Control Deck

> Method: script-generated KiCad (v3/tools, tracked in git this time), freerouting,
> home hand assembly with parts ordered from JLCPCB/LCSC. Purpose unchanged from V1:
> a physical control deck for AI workflows.

## Version naming (authoritative)

| Version | What it is | Where |
|---|---|---|
| V1 | 90×90 4-layer RP2040 board, JLC-assembled (rev 0.1, ordered 2026-07-28) | `hardware/` |
| V2 | V1 + PowerDeck two-deck concept (pogo/Qi), paper design | `~/kicad-projects/agentdeck-powerdeck` |
| V3 | THIS: bigger, hand-solderable, 24 keys, OLED, touch, LiPo, USB+BLE | `v3/` |

Enclosure files named "v2/v3-assembled.blend" are *assembly iterations of V1*, an
unfortunate collision; V3 outputs use the `AgentDeckV3-` prefix throughout.

## Feature set (from market research, see plan)

24-key 4×6 Choc matrix · per-key SK6812 · 0.96" OLED (model/layer/agent-state/battery)
· EC11 encoder · capacitive touch PTT pad · USB-C + BLE HID · 1000 mAh LiPo w/ USB-C
charging · power switch · same host protocol as V1 (`host/agentdeck_bridge.py`) + screen cmd.

## Architecture

```
USB-C (J1) ─ USBLC6 ESD ─ D+/D- ──────────────► ESP32-S3-WROOM-1 (U1)
   │ VBUS 5V                                      │ GPIO matrix 4 rows × 6 cols (24 keys
   ├──► TP4056 (U4) ──► BAT+ ──► JST-PH (J2) ─ LiPo│   + 24× 1N4148W)
   │        │ PROG 2.4k = 500 mA                  │ I2C → OLED (OLED1)
   │        └ CHRG/STDBY → status nets            │ T?  → TouchPad_D12 (native touch)
   ├──► Q1 AO3401A gate (load share: USB present  │ GPIO → EC11 A/B/SW
   │      disconnects battery from VSYS)          │ GPIO → LED_DATA → U2 AHCT125 → chain
   ▼                                              │ ADC → VBAT ÷ (100k/47k)
  VSYS (5V USB or 3.7–4.2V battery, diode-OR) ────┤ EN/IO0 ← BOOT/RESET tacts + prog pads
   ├──► SK6812 ×24 power rail (3.7–5.5V OK)       │
   └──► ME6211C33 (U5) ──► +3V3 ──► U1, OLED, pulls
        (low-Iq LDO; power switch SW25 in VSYS path)
```

Key GPIO budget (S3): 4+6 matrix, 2 I2C, 1 touch, 3 encoder, 1 LED data, 1 ADC,
2 status (CHRG/STDBY sense), spare ≥8. Strapping pins (GPIO0/3/45/46) kept free of
matrix duty per datasheet §strapping.

## Component placement rules (datasheet-driven)

Datasheets live in `docs/datasheets/` (V1 set) and `docs/datasheets/v3/`:
`esp32-s3-wroom-1_datasheet.pdf`, `esp32-s3-hw-design-guidelines.pdf`, `tp4056.pdf`,
plus V1's `sk6812mini-e.pdf`, `ttp223.pdf`. ME6211 + AO3401A sheets: fetch at order
time (LCSC links rotated). `v3/tools/place_pcb.py` implements these as constraints:

1. **ESP32-S3-WROOM antenna** (HW design guidelines §PCB layout): antenna end
   overhangs the board edge, or sits on an edge with **≥15 mm copper keepout** on all
   layers under/around the antenna; no traces, no pour, no silk. Module GND pad
   stitched with vias to bottom pour.
2. **Decoupling** (guidelines §power): 100 nF within **2 mm** of each module 3V3 pin;
   10 µF bulk within 10 mm; LDO in/out caps at the LDO pads (ME6211 needs ≥1 µF
   ceramic on out, X5R/X7R).
3. **USB differential pair** (V1 lore + guidelines): D+/D− routed as a coupled pair,
   length-matched ±0.5 mm, over solid ground, no layer change between connector, ESD
   part, and module; ESD diode (U3) placed at the connector, stubs minimized. On a
   2-layer 1.6 mm board true 90 Ω is not achievable, keep the pair **short (<15 mm)**
   which is fine at full-speed USB (V1 shipped the same compromise, documented).
4. **TP4056 thermal** (tp4056.pdf): it is a linear charger and dissipates
   (VBUS−VBAT)·Icharge ≈ 0.6 W worst case at 500 mA. Copper pour on its tab/GND pins
   ≥1 cm², thermal vias to bottom pour; keep ≥5 mm from the touch pad and battery.
5. **SK6812 chain** (sk6812mini-e.pdf): 100 nF per LED at its VDD; power injected at
   both chain ends (24 LEDs ≈ 1.4 A worst-case white, VSYS pour, not a trace);
   data line series 330 R at the head; keep data stubs < 5 mm.
6. **Touch pad** (S3 guidelines touch-sensor section): pad on top layer, **no ground
   pour directly under the pad** (hatch or void), trace to the touch pin thin
   (0.15 mm), short, away from LED data and USB; guard with grounded hatch ring.
7. **Matrix diodes**: cathode to row (COL2ROW), consistent orientation for firmware;
   diode next to its switch pad, not bussed at a distance.
8. **Load-share FET** (NeuralCard DESIGN.md §3): Q1 gate to VBUS with 100 k bleed,
   source to VSYS, drain to BAT side, battery isolated when USB present; place at
   the power entry corner with the TP4056.
9. **EC11/tacts/power switch**: mechanical parts on board edges per their drawings;
   MSK12C02 actuator overhangs the edge (NeuralCard pattern).
10. **OLED FPC tab**: solder tab lands on top edge strip; keep the flex bend radius
    area free of components for 5 mm behind the tab.

## PCB best practices adopted (2-layer)

- **Bottom layer = near-solid GND pour**; top pour GND in gaps; stitch vias on a
  ~10 mm grid and around every connector/IC (return-path rule: every signal has an
  adjacent ground return).
- Power distribution as pours/wide traces: VSYS pour region on top around the LED
  field; 3V3 min 0.5 mm trace ring.
- All vias ≥ 0.45/0.3 mm (standard fab bracket, pricing lesson from V1 rev0.1).
- Track/clearance defaults 0.2/0.2 mm (hand-friendly, easy fab); 0.15 only where the
  OLED tab forces it.
- Silkscreen: every ref + pin-1 marks + polarity bars; flashing instructions and
  pinout legend printed on the board (V1 style); text ≥1 mm height (JLC legibility , 
  V1 DRC lesson).
- No components under the battery pocket footprint (keepout zone in the PCB and a
  matching pocket in the case bottom).

## Firmware (v3/firmware, Arduino ESP32-S3)

Matrix scan/debounce → USB HID *and* BLE HID (NimBLE), auto-switch by USB presence;
OLED status UI; native touch → PTT; SK6812 state colors (V1 language: idle/think/
work/block/done/err); battery % from ADC; CDC protocol = V1's plus `S <line> <text>`.
USB name "AgentDeckV3" (agentdeck_bridge.py matches by name).

## Rules recap (see v3/PARTS.yaml header)

Manifest-first · 2D+3D dims verified by v3/tools/verify_parts.py · hand-solder floor
0.5 mm pitch · JLC/LCSC stock status per line · V1/V2 untouched · v3 tools tracked.

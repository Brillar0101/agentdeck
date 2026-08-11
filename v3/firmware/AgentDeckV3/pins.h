// ClaudeMicro V3 pin map - matches v3/tools/gen_schematic.py PINOUT table
// (generated 2026-07-28, ERC-clean rev). Diff against the generator's printed
// table whenever either side changes.
#pragma once

// 4x6 key matrix (COL2ROW: switch->diode anode, cathode->row)
constexpr int ROW_PINS[4] = {4, 5, 6, 7};
constexpr int COL_PINS[6] = {10, 11, 12, 13, 14, 15};
constexpr int NUM_ROWS = 4, NUM_COLS = 6, NUM_KEYS = 24;

// Peripherals
constexpr int PIN_LED_DATA = 21;   // SK6812 chain via AHCT125 (VSYS_SW rail)
constexpr int NUM_LEDS = 24;
constexpr int PIN_I2C_SDA = 8;     // OLED SSD1315 @0x3C
constexpr int PIN_I2C_SCL = 9;
constexpr int PIN_TOUCH = 1;       // T1 native touch
constexpr int PIN_ENC_A = 40;
constexpr int PIN_ENC_B = 41;
constexpr int PIN_ENC_SW = 42;
constexpr int PIN_VBAT_ADC = 2;    // ADC1_CH1, 100k/47k divider
constexpr int PIN_CHRG = 47;       // TP4056 CHRG (active low)
constexpr int PIN_STDBY = 48;      // TP4056 STDBY (active low)

// Battery divider: Vbat = ADC * (100+47)/47
constexpr float VBAT_DIVIDER = 147.0f / 47.0f;

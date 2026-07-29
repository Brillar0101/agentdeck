// ClaudeMicro V3 pin map - MUST match v3/tools/gen_schematic.py PINOUT table.
// This file is the firmware's copy of the hardware truth; gen_schematic.py
// prints its table at generation time - diff them when either changes.
// PLACEHOLDER VALUES until Phase 1 finalizes the map (marked TODO-PIN).
#pragma once

// 4x6 key matrix (COL2ROW: diode cathode to row)
constexpr int ROW_PINS[4] = {4, 5, 6, 7};          // TODO-PIN
constexpr int COL_PINS[6] = {8, 9, 10, 11, 12, 13}; // TODO-PIN
constexpr int NUM_ROWS = 4, NUM_COLS = 6, NUM_KEYS = 24;

// Peripherals
constexpr int PIN_LED_DATA = 21;   // TODO-PIN  SK6812 chain via AHCT125
constexpr int NUM_LEDS = 24;
constexpr int PIN_I2C_SDA = 17;    // TODO-PIN  OLED
constexpr int PIN_I2C_SCL = 18;    // TODO-PIN
constexpr int PIN_TOUCH = 14;      // TODO-PIN  must be touch-capable (GPIO1-14)
constexpr int PIN_ENC_A = 15;      // TODO-PIN
constexpr int PIN_ENC_B = 16;      // TODO-PIN
constexpr int PIN_ENC_SW = 47;     // TODO-PIN
constexpr int PIN_VBAT_ADC = 2;    // TODO-PIN  100k/47k divider
constexpr int PIN_CHRG = 41;       // TODO-PIN  TP4056 CHRG (active low)
constexpr int PIN_STDBY = 42;      // TODO-PIN  TP4056 STDBY (active low)

// Battery divider: Vbat = ADC * (100+47)/47
constexpr float VBAT_DIVIDER = 147.0f / 47.0f;

// ClaudeMicro V4 pin map - matches v4/tools/gen_schematic.py PINOUT table
// (FINAL, closed). Diff against the generator's printed table whenever
// either side changes.
#pragma once

// 4x6 key matrix (COL2ROW: switch->diode anode, cathode->row)
constexpr int ROW_PINS[4] = {4, 5, 6, 7};
constexpr int COL_PINS[6] = {10, 11, 12, 13, 14, 15};
constexpr int NUM_ROWS = 4, NUM_COLS = 6, NUM_KEYS = 24;

// Peripherals
constexpr int PIN_LED_DATA = 21;   // SK6812 chain via AHCT125 (VSYS_SW rail)
constexpr int NUM_LEDS = 24;
constexpr int PIN_I2C_SDA = 8;     // LCD touch controller (CST816-class @0x15)
constexpr int PIN_I2C_SCL = 9;
constexpr int PIN_TOUCH = 1;       // T1 native touch (PTT pad)
constexpr int PIN_ENC_A = 40;      // first EC11
constexpr int PIN_ENC_B = 41;
constexpr int PIN_ENC_SW = 42;
constexpr int PIN_ENC2_A = 35;     // second EC11
constexpr int PIN_ENC2_B = 36;
constexpr int PIN_ENC2_SW = 37;
constexpr int PIN_VBAT_ADC = 2;    // ADC1_CH1, 100k/47k divider

// LCD: ST7789 240x280 SPI. CS tied low in hardware, RST tied to EN,
// backlight always-on - only SCK/MOSI/DC reach the MCU.
constexpr int PIN_LCD_SCK = 16;
constexpr int PIN_LCD_MOSI = 17;
constexpr int PIN_LCD_DC = 18;

// I2S full duplex: shared BCLK/WS; DOUT -> NS4168 amp (CTRL=VDD: right
// slot), DIN <- MEMS mic (left slot). Replaces V3's CHRG/STDBY on 47/48
// (TP4056 status pins are no-connect in V4).
constexpr int PIN_I2S_BCLK = 38;
constexpr int PIN_I2S_WS = 39;
constexpr int PIN_I2S_DOUT = 47;
constexpr int PIN_I2S_DIN = 48;

// Battery divider: Vbat = ADC * (100+47)/47
constexpr float VBAT_DIVIDER = 147.0f / 47.0f;

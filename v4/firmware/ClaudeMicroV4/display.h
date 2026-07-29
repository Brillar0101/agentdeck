// ST7789 240x280 LCD UI (replaces the V3 OLED). V3's uiTick throttle
// pattern; the S-protocol status lines land here.
#pragma once
#include <stdint.h>

constexpr int LCD_W = 240, LCD_H = 280;
// Soft-key hint row: 4 zones across the bottom of the panel. touch.cpp maps
// taps in this band to "TK <n>" host events.
constexpr int NUM_SOFTKEYS = 4;
constexpr int SOFTKEY_Y0 = 236;          // top of the soft-key band
constexpr int SOFTKEY_W = LCD_W / NUM_SOFTKEYS;

void displayBegin();
void displaySplash();
void displayTick();                       // throttled full redraw (V3 uiTick)
void displaySetLine(int line, const char *text);   // S <line 0-3> <text>
void displayMarkDirty();

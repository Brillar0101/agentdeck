// ST7789 240x280 over SPI (Adafruit GFX). Header + 4 status lines +
// soft-key hint row. CS is tied low and RST tied to EN in hardware, so the
// driver gets -1 for both and only SCK/MOSI/DC are wired.
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include "pins.h"
#include "keymap.h"
#include "ble_hid.h"
#include "support.h"
#include "display.h"

// 240x280 1.69" panels sit centered in the ST7789's 240x320 RAM: row offset
// (320-280)/2 = 20. Adafruit_ST7789::init(240, 280) applies exactly that
// offset, so no manual setRowStart is needed - verify on first hardware.
static Adafruit_ST7789 tft(&SPI, /*CS*/ -1, PIN_LCD_DC, /*RST*/ -1);

static char statusLines[4][22] = {"ClaudeMicro V4", "", "", ""};
static bool dirty = true;

// 16-bit 565 palette (kept muted to match the SK6812 state language)
constexpr uint16_t COL_BG = 0x0000, COL_FG = 0xEF7D, COL_DIM = 0x8410;
constexpr uint16_t COL_ACCENT = 0x64BF, COL_HDR = 0xFEA0;

void displayBegin() {
  SPI.begin(PIN_LCD_SCK, /*MISO*/ -1, PIN_LCD_MOSI, /*SS*/ -1);
  tft.init(LCD_W, LCD_H);        // sets the 240x280 row offset (20)
  tft.setSPISpeed(40000000);
  tft.setRotation(0);            // portrait, connector at the bottom
  tft.fillScreen(COL_BG);
}

void displaySplash() {
  tft.fillScreen(COL_BG);
  tft.setTextSize(3);
  tft.setTextColor(COL_HDR);
  tft.setCursor(12, 110);
  tft.print("ClaudeMicro");
  tft.setTextSize(2);
  tft.setTextColor(COL_DIM);
  tft.setCursor(12, 144);
  tft.print("V4  voice + screen");
}

void displaySetLine(int line, const char *text) {
  if (line < 0 || line > 3) return;
  strncpy(statusLines[line], text, 21);
  statusLines[line][21] = 0;
  dirty = true;
}

void displayMarkDirty() { dirty = true; }

static float readVbat() {
  return analogReadMilliVolts(PIN_VBAT_ADC) / 1000.0f * VBAT_DIVIDER;
}

static void drawHeader() {
  char hdr[24];
  float vb = readVbat();
  int pct = (int)((vb - 3.3f) / (4.2f - 3.3f) * 100.0f);
  pct = pct < 0 ? 0 : (pct > 100 ? 100 : pct);
  // V4 has no TP4056 CHRG sense (IO47/48 went to I2S); USB present is the
  // best available "charging" proxy - the load-share path charges whenever
  // VBUS is up.
  bool chg = usbMounted();
  snprintf(hdr, sizeof(hdr), "L%d %s %3d%%%s", currentLayer,
           bleConnected() ? "BLE" : "USB", pct, chg ? "+" : " ");
  tft.fillRect(0, 0, LCD_W, 24, COL_BG);
  tft.setTextSize(2);
  tft.setTextColor(COL_HDR);
  tft.setCursor(4, 4);
  tft.print(hdr);
  tft.drawFastHLine(0, 26, LCD_W, COL_DIM);
}

static void drawStatusLines() {
  tft.fillRect(0, 30, LCD_W, SOFTKEY_Y0 - 34, COL_BG);
  tft.setTextSize(2);
  tft.setTextColor(COL_FG);
  for (int i = 0; i < 4; i++) {
    tft.setCursor(4, 40 + i * 26);
    tft.print(statusLines[i]);
  }
}

static void drawSoftKeys() {
  tft.fillRect(0, SOFTKEY_Y0, LCD_W, LCD_H - SOFTKEY_Y0, COL_BG);
  tft.setTextSize(2);
  tft.setTextColor(COL_ACCENT);
  for (int i = 0; i < NUM_SOFTKEYS; i++) {
    int x = i * SOFTKEY_W;
    tft.drawRoundRect(x + 2, SOFTKEY_Y0 + 2, SOFTKEY_W - 4,
                      LCD_H - SOFTKEY_Y0 - 4, 4, COL_DIM);
    tft.setCursor(x + SOFTKEY_W / 2 - 11, SOFTKEY_Y0 + 15);
    tft.printf("K%d", i + 1);      // host maps TK <n>; labels TODO via host
  }
}

void displayTick() {
  static uint32_t last = 0;
  if (!dirty && millis() - last < 500) return;   // V3 uiTick throttle
  last = millis();
  dirty = false;
  drawHeader();
  drawStatusLines();
  drawSoftKeys();
}

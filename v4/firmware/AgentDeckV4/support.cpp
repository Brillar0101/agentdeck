// Encoders, touch PTT, host CDC protocol. Ported from V3; the OLED UI moved
// to display.cpp (ST7789) and the protocol gained N (beep) and R (mic RMS).
#include <Adafruit_NeoPixel.h>
#include "USBHIDKeyboard.h"
#include "pins.h"
#include "keymap.h"
#include "ble_hid.h"
#include "display.h"
#include "audio.h"
#include "support.h"

extern Adafruit_NeoPixel leds;
extern USBHIDKeyboard usbKeyboard;

// ---- state colors (V1 language) ----
struct StateColor { const char *name; uint8_t r, g, b; };
static const StateColor STATES[] = {
  {"idle", 8, 8, 12}, {"think", 40, 20, 60}, {"work", 10, 40, 70},
  {"block", 80, 30, 0}, {"done", 10, 60, 15}, {"err", 80, 5, 5},
  {"off", 0, 0, 0},
};

// LED chain is serpentine over the 4x6 key grid (place_pcb.py): row r, col c
// -> LED r*6 + (r even ? c : 5-c). Agent keys are row 1 (indices 6..11).
static int keyToLed(int key) {
  int r = key / 6, c = key % 6;
  return r * 6 + ((r % 2) == 0 ? c : 5 - c);
}

static bool touchActive = false;
static uint32_t touchBaseline = 0;

// ---- encoders (polled quadrature, V3 pattern) ----
static const int8_t QUAD_DIR[16] = {0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};

static uint8_t encPrev = 0;
void pollEncoder() {
  uint8_t a = digitalRead(PIN_ENC_A), b = digitalRead(PIN_ENC_B);
  uint8_t cur = (a << 1) | b;
  if (cur != encPrev) {
    int8_t d = QUAD_DIR[(encPrev << 2) | cur];
    if (d) Serial.printf("E %d\n", d);
    encPrev = cur;
  }
}

static uint8_t enc2Prev = 0;
static bool enc2SwState = false;
static uint32_t enc2SwDebounce = 0;
void pollEncoder2() {
  uint8_t a = digitalRead(PIN_ENC2_A), b = digitalRead(PIN_ENC2_B);
  uint8_t cur = (a << 1) | b;
  if (cur != enc2Prev) {
    int8_t d = QUAD_DIR[(enc2Prev << 2) | cur];
    if (d) Serial.printf("F %d\n", d);
    enc2Prev = cur;
  }
  bool sw = digitalRead(PIN_ENC2_SW) == LOW;
  if (sw != enc2SwState && millis() - enc2SwDebounce > 15) {
    enc2SwState = sw;
    enc2SwDebounce = millis();
    Serial.printf("FS %d\n", sw ? 1 : 0);
  }
}

// ---- native touch PTT ----
void pollTouch() {
  uint32_t v = touchRead(PIN_TOUCH);
  if (touchBaseline == 0) { touchBaseline = v; return; }   // first-call calibration
  bool active = v > touchBaseline + touchBaseline / 5;      // +20% threshold (S3: rises)
  if (active != touchActive) {
    touchActive = active;
    Serial.printf("T %d\n", active ? 1 : 0);
  }
}

// ---- host protocol ----
static void applyState(int led, const char *state) {
  if (led < 0 || led >= NUM_LEDS) return;
  for (const auto &s : STATES)
    if (strcmp(s.name, state) == 0) {
      leds.setPixelColor(led, leds.Color(s.r, s.g, s.b));
      leds.show();
      return;
    }
}

void pollHostSerial() {
  static char line[96];
  static size_t n = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c != '\n' && n < sizeof(line) - 1) { line[n++] = c; continue; }
    line[n] = 0; n = 0;
    int a1, a2, a3; char text[80];
    // G <slot 1-6> = V1 agent slots -> the AGENT keys on row 1
    if (sscanf(line, "G %d %79s", &a1, text) == 2 && a1 >= 1 && a1 <= 6)
      applyState(keyToLed(6 + a1 - 1), text);
    else if (sscanf(line, "A %d %79s", &a1, text) == 2) applyState(a1, text);
    else if (sscanf(line, "B %d %d %d", &a1, &a2, &a3) == 3) {
      for (int i = 0; i < NUM_LEDS; i++) leds.setPixelColor(i, leds.Color(a1, a2, a3));
      leds.show();
    } else if (line[0] == 'X') { leds.clear(); leds.show(); }
    else if (line[0] == 'P') Serial.println("P ClaudeMicroV4 1");
    else if (sscanf(line, "S %d %79[^\n]", &a1, text) == 2 && a1 >= 0 && a1 < 4)
      displaySetLine(a1, text);
    else if (sscanf(line, "N %d %d", &a1, &a2) == 2)     // notification tone
      audioBeep(a1, a2);
    else if (line[0] == 'R')                             // mic sanity (bring-up)
      Serial.printf("R %.0f\n", audioMicRms());
  }
}

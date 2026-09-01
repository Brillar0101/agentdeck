// Encoder, 5-way joystick, host CDC protocol, OLED UI.
#include <Adafruit_NeoPixel.h>
#include <U8g2lib.h>
#include "USBHIDKeyboard.h"
#include "pins.h"
#include "keymap.h"
#include "ble_hid.h"
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

// LED chain is serpentine over the 4x5 key grid (place_pcb.py): row r, col c
// -> LED r*5 + (r even ? c : 4-c). Agent keys: slots 1-5 = row 1, 6-8 = row 2.
static int keyToLed(int key) {
  int r = key / 5, c = key % 5;
  return r * 5 + ((r % 2) == 0 ? c : 4 - c);
}
static int agentSlotKey(int slot) {          // slot 1..8 -> key index
  return slot <= 5 ? 5 + slot - 1 : 10 + slot - 6;
}

static char oledLines[4][22] = {"AgentDeck V2", "", "", ""};
static bool oledDirty = true;

// ---- encoder (polled quadrature) ----
static uint8_t encPrev = 0;
void pollEncoder() {
  uint8_t a = digitalRead(PIN_ENC_A), b = digitalRead(PIN_ENC_B);
  uint8_t cur = (a << 1) | b;
  if (cur != encPrev) {
    static const int8_t DIR[16] = {0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
    int8_t d = DIR[(encPrev << 2) | cur];
    if (d) Serial.printf("E %d\n", d);
    encPrev = cur;
  }
}

// ---- 5-way joystick (active low, pullups) ----
// Outbound "J <U|D|L|R|C> <1|0>" on every edge; the host bridge maps it
// (session scroll, menu navigation). Debounced per direction.
void pollJoystick() {
  static const int PINS[5] = {PIN_JOY_UP, PIN_JOY_DOWN, PIN_JOY_LEFT,
                              PIN_JOY_RIGHT, PIN_JOY_CTR};
  static const char NAMES[5] = {'U', 'D', 'L', 'R', 'C'};
  static bool state[5] = {};
  static uint32_t last[5] = {};
  for (int i = 0; i < 5; i++) {
    bool active = digitalRead(PINS[i]) == LOW;
    if (active != state[i] && millis() - last[i] > 8) {
      state[i] = active; last[i] = millis();
      Serial.printf("J %c %d\n", NAMES[i], active ? 1 : 0);
    }
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
    // G <slot 1-8> = agent slots -> the AGENT keys on rows 1-2
    if (sscanf(line, "G %d %79s", &a1, text) == 2 && a1 >= 1 && a1 <= 8)
      applyState(keyToLed(agentSlotKey(a1)), text);
    else if (sscanf(line, "A %d %79s", &a1, text) == 2) applyState(a1, text);
    else if (sscanf(line, "B %d %d %d", &a1, &a2, &a3) == 3) {
      for (int i = 0; i < NUM_LEDS; i++) leds.setPixelColor(i, leds.Color(a1, a2, a3));
      leds.show();
    } else if (line[0] == 'X') { leds.clear(); leds.show(); }
    else if (line[0] == 'P') Serial.println("P AgentDeckV2 1");
    else if (sscanf(line, "S %d %79[^\n]", &a1, text) == 2 && a1 >= 0 && a1 < 4) {
      strncpy(oledLines[a1], text, 21); oledLines[a1][21] = 0; oledDirty = true;
    }
  }
}

void uiMarkDirty() { oledDirty = true; }

// ---- OLED UI ----
void uiSplash(U8G2 &oled) {
  oled.clearBuffer();
  oled.setFont(u8g2_font_7x13B_tr);
  oled.drawStr(10, 24, "AgentDeck V2");
  oled.setFont(u8g2_font_5x8_tr);
  oled.drawStr(10, 40, "AI control deck");
  oled.sendBuffer();
}

static float readVbat() {
  return analogReadMilliVolts(PIN_VBAT_ADC) / 1000.0f * VBAT_DIVIDER;
}

void uiTick(U8G2 &oled) {
  static uint32_t last = 0;
  if (!oledDirty && millis() - last < 500) return;
  last = millis(); oledDirty = false;

  oled.clearBuffer();
  oled.setFont(u8g2_font_5x8_tr);
  char hdr[24];
  float vb = readVbat();
  int pct = (int)((vb - 3.3f) / (4.2f - 3.3f) * 100.0f);
  pct = pct < 0 ? 0 : (pct > 100 ? 100 : pct);
  bool chg = digitalRead(PIN_CHRG) == LOW;
  snprintf(hdr, sizeof(hdr), "L%d %s %3d%%%s", currentLayer,
           bleConnected() ? "BLE" : "USB", pct, chg ? "+" : "");
  oled.drawStr(0, 8, hdr);
  oled.drawHLine(0, 10, 128);
  for (int i = 0; i < 4; i++) oled.drawStr(0, 22 + i * 11, oledLines[i]);
  oled.sendBuffer();
}

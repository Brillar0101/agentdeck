/* ClaudeMicro V3 firmware - ESP32-S3, USB HID + BLE HID, OLED, touch PTT.
 *
 * Build: arduino-cli compile --fqbn esp32:esp32:esp32s3:USBMode=hwcdc,\
 *        CDCOnBoot=cdc,FlashSize=8M,PSRAM=opi  v3/firmware/ClaudeMicroV3
 * Libraries: Adafruit_NeoPixel, U8g2 (OLED), NimBLE-Arduino, ESP32-USB-HID (core).
 *
 * Host protocol (CDC, newline-delimited ASCII) = V1's plus screen:
 *   inbound:  G <slot> <state> | A <led> <state> | B <r> <g> <b> | X | P
 *             S <line> <text>          (NEW: write OLED status line 0-3)
 *   outbound: K <role> <0|1> | E <+-1> | J ... (no joystick on V3) | T <0|1> (touch)
 * States: idle think work block done err (V1 color language).
 */
#include <Adafruit_NeoPixel.h>
#include <U8g2lib.h>
#include <Wire.h>
#include "USB.h"
#include "USBHIDKeyboard.h"
#include "pins.h"
#include "keymap.h"
#include "ble_hid.h"
#include "support.h"

USBHIDKeyboard usbKeyboard;
Adafruit_NeoPixel leds(NUM_LEDS, PIN_LED_DATA, NEO_GRB + NEO_KHZ800);
U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

bool keyState[NUM_KEYS] = {};
uint32_t keyDebounce[NUM_KEYS] = {};
constexpr uint32_t DEBOUNCE_MS = 8;

bool usbMounted() { return USB; }  // refined at bring-up: tud_mounted()

void sendKey(uint8_t keyIndex, bool pressed) {
  const KeyBinding &b = KEYMAP[currentLayer][keyIndex];
  if (usbMounted()) {
    if (pressed) usbKeyboard.pressRaw(b.keycode); else usbKeyboard.releaseRaw(b.keycode);
    if (b.mods) { /* modifiers handled in keymap.cpp helper */ }
  } else {
    bleSendKey(b, pressed);
  }
  Serial.printf("K %d %d\n", keyIndex, pressed ? 1 : 0);
}

void scanMatrix() {
  for (int r = 0; r < NUM_ROWS; r++) {
    digitalWrite(ROW_PINS[r], LOW);
    delayMicroseconds(5);
    for (int c = 0; c < NUM_COLS; c++) {
      int idx = r * NUM_COLS + c;
      bool pressed = digitalRead(COL_PINS[c]) == LOW;
      if (pressed != keyState[idx] && millis() - keyDebounce[idx] > DEBOUNCE_MS) {
        keyState[idx] = pressed;
        keyDebounce[idx] = millis();
        sendKey(idx, pressed);
      }
    }
    digitalWrite(ROW_PINS[r], HIGH);
  }
}

void setup() {
  for (int r = 0; r < NUM_ROWS; r++) { pinMode(ROW_PINS[r], OUTPUT); digitalWrite(ROW_PINS[r], HIGH); }
  for (int c = 0; c < NUM_COLS; c++) pinMode(COL_PINS[c], INPUT_PULLUP);
  pinMode(PIN_ENC_A, INPUT_PULLUP); pinMode(PIN_ENC_B, INPUT_PULLUP);
  pinMode(PIN_ENC_SW, INPUT_PULLUP);
  pinMode(PIN_CHRG, INPUT_PULLUP); pinMode(PIN_STDBY, INPUT_PULLUP);

  leds.begin(); leds.setBrightness(60); leds.show();
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  oled.begin();
  usbKeyboard.begin(); USB.begin();
  bleBegin("ClaudeMicroV3");
  Serial.begin(115200);
  uiSplash(oled);
}

void loop() {
  scanMatrix();
  pollEncoder();
  pollTouch();       // native touchRead(PIN_TOUCH) vs calibrated threshold -> PTT
  pollHostSerial();  // G/A/B/X/P/S commands -> LED + OLED state
  uiTick(oled);      // battery %, layer, agent states, BLE/USB indicator
}

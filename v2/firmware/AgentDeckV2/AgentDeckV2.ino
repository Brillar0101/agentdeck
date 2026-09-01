/* AgentDeck V2 firmware - ESP32-S3, USB HID + BLE HID, OLED, 5-way joystick.
 *
 * Build (native USB HID needs TinyUSB/OTG mode; N8R2 = 8MB flash, QSPI PSRAM):
 *   arduino-cli compile --fqbn \
 *     esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=enabled \
 *     v2/firmware/AgentDeckV2
 * Libraries: Adafruit_NeoPixel, U8g2 (OLED), NimBLE-Arduino.
 *
 * Host protocol (CDC, newline-delimited ASCII) = V1's plus screen:
 *   inbound:  G <slot 1-8> <state> (agent-key LEDs) | A <led> <state> |
 *             B <r> <g> <b> | X | P
 *             S <line 0-3> <text>      (NEW: write OLED status line)
 *   outbound: K <idx> <0|1> <role> | E <+-1> | J <U|D|L|R|C> <0|1> | L <mode>
 * System row (INT/PTT/REC/DND) is reported as K lines; the bridge acts on the
 * role. MODE cycles modes in firmware. Row 0 is identical in every mode.
 * States: idle think work block done err off (V1 color language).
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

extern "C" bool tud_mounted(void);   // TinyUSB: USB configured by a host
bool usbMounted() { return tud_mounted(); }

static void specialKey(const KeyBinding &b, bool pressed) {
  if (!pressed || strcmp(b.role, "MODE") != 0) return;   // other roles: host acts on K line
  currentLayer = (currentLayer + 1) % NUM_LAYERS;
  Serial.printf("L %d\n", currentLayer);
  uiMarkDirty();
}

void sendKey(uint8_t keyIndex, bool pressed) {
  const KeyBinding &b = KEYMAP[currentLayer][keyIndex];
  if (b.keycode == 0) {
    specialKey(b, pressed);            // MODE in firmware; INT/PTT/REC/DND/packs via host
  } else if (usbMounted()) {
    for (int i = 0; i < 8; i++)        // HID modifier usages 0xE0..0xE7
      if (b.mods & (1 << i)) {
        if (pressed) usbKeyboard.pressRaw(0xE0 + i);
        else usbKeyboard.releaseRaw(0xE0 + i);
      }
    if (pressed) usbKeyboard.pressRaw(b.keycode);
    else usbKeyboard.releaseRaw(b.keycode);
  } else {
    bleSendKey(b, pressed);
  }
  Serial.printf("K %d %d %s\n", keyIndex, pressed ? 1 : 0, b.role);
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
  for (int p : {PIN_JOY_UP, PIN_JOY_DOWN, PIN_JOY_LEFT, PIN_JOY_RIGHT, PIN_JOY_CTR})
    pinMode(p, INPUT_PULLUP);

  leds.begin(); leds.setBrightness(60); leds.show();
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  oled.begin();
  USB.productName("AgentDeckV2");    // agentdeck_bridge.py matches by name
  USB.manufacturerName("princetekki");
  usbKeyboard.begin(); USB.begin();
  bleBegin("AgentDeckV2");
  Serial.begin(115200);
  uiSplash(oled);
}

void loop() {
  scanMatrix();
  pollEncoder();
  pollJoystick();    // J <dir> <0|1> edges to the host
  pollHostSerial();  // G/A/B/X/P/S commands -> LED + OLED state
  uiTick(oled);      // battery %, layer, agent states, BLE/USB indicator
}

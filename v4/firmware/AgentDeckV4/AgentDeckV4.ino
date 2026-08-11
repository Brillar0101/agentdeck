/* AgentDeck V4 firmware - ESP32-S3, USB HID + BLE HID, ST7789 touch LCD,
 * I2S voice (MEMS mic + NS4168 amp), wake word, touch PTT, 2x EC11.
 *
 * Build (native USB HID needs TinyUSB/OTG mode; N8R2 = 8MB flash, QSPI PSRAM):
 *   arduino-cli compile --fqbn \
 *     esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=enabled \
 *     v4/firmware/AgentDeckV4
 * Libraries: Adafruit_NeoPixel, Adafruit GFX + "Adafruit ST7735 and ST7789",
 * NimBLE-Arduino; ESP_I2S/ESP_SR come with the esp32 core (3.x).
 *
 * Host protocol (CDC, newline-delimited ASCII) = V3's plus audio + touch:
 *   inbound:  G <slot 1-6> <state> (agent-key LEDs) | A <led> <state> |
 *             B <r> <g> <b> | X | P
 *             S <line 0-3> <text>      (LCD status line, was OLED in V3)
 *             N <freq> <ms>            (NEW: notification beep via amp)
 *             R                        (NEW: reply "R <rms>" mic sanity)
 *   outbound: K <idx> <0|1> <role> | E <+-1> | T <0|1> (touch PTT) | L <layer>
 *             F <+-1> | FS <0|1>       (NEW: ENC2 rotation / switch)
 *             TK <n>                   (NEW: LCD soft-key tap, 1-4)
 *             W 1                      (NEW: wake word detected)
 * States: idle think work block done err off (V1 color language).
 */
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include "USB.h"
#include "USBHIDKeyboard.h"
#include "pins.h"
#include "keymap.h"
#include "ble_hid.h"
#include "display.h"
#include "touch.h"
#include "audio.h"
#include "support.h"

USBHIDKeyboard usbKeyboard;
Adafruit_NeoPixel leds(NUM_LEDS, PIN_LED_DATA, NEO_GRB + NEO_KHZ800);

bool keyState[NUM_KEYS] = {};
uint32_t keyDebounce[NUM_KEYS] = {};
constexpr uint32_t DEBOUNCE_MS = 8;

extern "C" bool tud_mounted(void);   // TinyUSB: USB configured by a host
bool usbMounted() { return tud_mounted(); }

static void specialKey(const KeyBinding &b, bool pressed) {
  if (!pressed) return;
  if (strcmp(b.role, "LAYER+") == 0 && currentLayer < NUM_LAYERS - 1) currentLayer++;
  else if (strcmp(b.role, "LAYER-") == 0 && currentLayer > 0) currentLayer--;
  else return;
  Serial.printf("L %d\n", currentLayer);
  displayMarkDirty();
}

void sendKey(uint8_t keyIndex, bool pressed) {
  const KeyBinding &b = KEYMAP[currentLayer][keyIndex];
  if (b.keycode == 0) {
    specialKey(b, pressed);            // LAYER+/-, FN, PTTLOCK, host macros
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
  pinMode(PIN_ENC2_A, INPUT_PULLUP); pinMode(PIN_ENC2_B, INPUT_PULLUP);
  pinMode(PIN_ENC2_SW, INPUT_PULLUP);

  leds.begin(); leds.setBrightness(60); leds.show();
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  USB.productName("AgentDeckV4");    // agentdeck_bridge.py matches "AgentDeck"
  USB.manufacturerName("princetekki");
  usbKeyboard.begin(); USB.begin();
  bleBegin("AgentDeckV4");
  Serial.begin(115200);
  displayBegin();
  touchPanelBegin();
  audioBegin();
  displaySplash();
}

void loop() {
  scanMatrix();
  pollEncoder();
  pollEncoder2();
  pollTouch();        // native touchRead(PIN_TOUCH) vs calibrated threshold -> PTT
  touchPanelPoll();   // CST816 polled @30 Hz -> TK soft-key events
  pollHostSerial();   // G/A/B/X/P/S/N/R commands -> LED + LCD + audio
  audioPoll();        // deferred wake-word event -> W 1 + LED flash
  displayTick();      // battery %, layer, agent states, BLE/USB indicator
}

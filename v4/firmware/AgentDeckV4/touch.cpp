// CST816-class capacitive touch over I2C, POLLED. The module's INT pin is
// not routed in V4, so we read the point registers at ~30 Hz inside the UI
// cadence. Non-touch panel variants simply never ACK 0x15 - stay silent.
#include <Arduino.h>
#include <Wire.h>
#include "display.h"
#include "touch.h"

constexpr uint8_t CST816_ADDR = 0x15;
// Register file (CST816S/T/D common map): 0x01 gesture, 0x02 finger count,
// 0x03/0x04 X hi/lo (hi nibble = event flag), 0x05/0x06 Y hi/lo.
constexpr uint8_t REG_GESTURE = 0x01;

static bool present = false;
static bool wasDown = false;

void touchPanelBegin() {
  Wire.beginTransmission(CST816_ADDR);
  present = (Wire.endTransmission() == 0);
  // No ACK -> non-touch module variant fitted; disable silently.
}

bool touchPanelPresent() { return present; }

static bool readPoint(int &x, int &y) {
  Wire.beginTransmission(CST816_ADDR);
  Wire.write(REG_GESTURE);
  if (Wire.endTransmission(false) != 0) return false;
  uint8_t buf[6];
  if (Wire.requestFrom(CST816_ADDR, (uint8_t)6) != 6) return false;
  for (auto &b : buf) b = Wire.read();
  if ((buf[1] & 0x0F) == 0) return false;          // no finger down
  x = ((buf[2] & 0x0F) << 8) | buf[3];
  y = ((buf[4] & 0x0F) << 8) | buf[5];
  return true;
}

void touchPanelPoll() {
  static uint32_t last = 0;
  if (!present || millis() - last < 33) return;    // ~30 Hz
  last = millis();

  int x = 0, y = 0;
  bool down = readPoint(x, y);
  if (down && !wasDown && y >= SOFTKEY_Y0) {
    int n = x / SOFTKEY_W + 1;                     // soft keys are 1-based
    if (n >= 1 && n <= NUM_SOFTKEYS) Serial.printf("TK %d\n", n);
  }
  wasDown = down;
}

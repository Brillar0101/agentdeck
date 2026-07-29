// Minimal BLE HID keyboard on NimBLE 2.x. Advertises when USB absent.
#include <NimBLEDevice.h>
#include <NimBLEHIDDevice.h>
#include "ble_hid.h"

static NimBLEHIDDevice *hid = nullptr;
static NimBLECharacteristic *input = nullptr;
static bool connected = false;

// Standard boot keyboard report descriptor
static const uint8_t REPORT_MAP[] = {
  0x05,0x01, 0x09,0x06, 0xA1,0x01, 0x85,0x01,
  0x05,0x07, 0x19,0xE0, 0x29,0xE7, 0x15,0x00, 0x25,0x01,
  0x75,0x01, 0x95,0x08, 0x81,0x02,               // modifiers
  0x95,0x01, 0x75,0x08, 0x81,0x01,               // reserved
  0x95,0x06, 0x75,0x08, 0x15,0x00, 0x25,0x65,
  0x05,0x07, 0x19,0x00, 0x29,0x65, 0x81,0x00,    // 6 keys
  0xC0
};

class ServerCB : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer *, NimBLEConnInfo &) override { connected = true; }
  void onDisconnect(NimBLEServer *, NimBLEConnInfo &, int) override {
    connected = false;
    NimBLEDevice::startAdvertising();
  }
};

void bleBegin(const char *name) {
  NimBLEDevice::init(name);
  auto *server = NimBLEDevice::createServer();
  server->setCallbacks(new ServerCB());
  hid = new NimBLEHIDDevice(server);
  input = hid->getInputReport(1);
  hid->setManufacturer("princetekki");
  hid->setPnp(0x02, 0x1209, 0xC1AD, 0x0003);   // pid.codes-style VID/PID
  hid->setHidInfo(0x00, 0x01);
  hid->setReportMap((uint8_t *)REPORT_MAP, sizeof(REPORT_MAP));
  hid->startServices();
  auto *adv = NimBLEDevice::getAdvertising();
  adv->setAppearance(HID_KEYBOARD);
  adv->addServiceUUID(hid->getHidService()->getUUID());
  adv->start();
}

bool bleConnected() { return connected; }

void bleSendKey(const KeyBinding &b, bool pressed) {
  if (!connected || !input) return;
  uint8_t report[8] = {};
  if (pressed) {
    report[0] = b.mods;
    report[2] = b.keycode;
  }
  input->setValue(report, sizeof(report));
  input->notify();
}

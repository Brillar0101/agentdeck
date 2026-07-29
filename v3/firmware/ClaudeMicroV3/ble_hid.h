// BLE HID keyboard via NimBLE - active when USB is not mounted.
#pragma once
#include "keymap.h"

void bleBegin(const char *name);
bool bleConnected();
void bleSendKey(const KeyBinding &b, bool pressed);

// Declarations for support.cpp (encoder/joystick/host protocol/OLED UI).
#pragma once
#include <U8g2lib.h>

void pollEncoder();
void pollJoystick();
void pollHostSerial();
void uiSplash(U8G2 &oled);
void uiTick(U8G2 &oled);
void uiMarkDirty();

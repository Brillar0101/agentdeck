// Declarations for support.cpp (encoder/touch/host protocol/OLED UI).
#pragma once
#include <U8g2lib.h>

void pollEncoder();
void pollTouch();
void pollHostSerial();
void uiSplash(U8G2 &oled);
void uiTick(U8G2 &oled);

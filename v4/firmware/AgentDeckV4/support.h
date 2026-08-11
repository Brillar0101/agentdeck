// Declarations for support.cpp (encoders/touch PTT/host protocol).
#pragma once

void pollEncoder();      // ENC1 -> "E <+-1>"
void pollEncoder2();     // ENC2 -> "F <+-1>", switch -> "FS <0|1>"
void pollTouch();        // native touch pad PTT -> "T <0|1>"
void pollHostSerial();   // G/A/B/X/P/S/N/R commands

bool usbMounted();       // defined in the .ino (TinyUSB mount state)

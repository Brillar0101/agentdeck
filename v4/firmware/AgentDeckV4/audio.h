// I2S full-duplex audio: MEMS mic in (left slot), NS4168 amp out (right
// slot, mono duplicated to both), plus ESP-SR wake word when a model
// partition is present.
#pragma once
#include <stdint.h>

bool audioBegin();                  // I2S up; wake word if model available
void audioPoll();                   // deferred wake-word event -> "W 1" + flash
void audioBeep(int freqHz, int ms); // notification tone (host: N <freq> <ms>)
float audioMicRms();                // mic sanity; -1 when SR owns the RX path
bool audioWakeWordActive();

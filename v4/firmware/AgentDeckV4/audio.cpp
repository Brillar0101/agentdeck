// ESP_I2S full duplex @16 kHz / 16-bit / stereo slots on one bus:
// DIN <- MEMS mic (left slot), DOUT -> NS4168 (CTRL=VDD reads the RIGHT
// slot, so mono TX is duplicated into both slots). Wake word via the core's
// ESP_SR ("Hi ESP" WakeNet9 - the stock model compiled into this core;
// custom "hey Claude" needs Espressif model training, documented TODO).
//
// The stock esp_sr partition scheme is 16MB-only; our N8R2 is 8MB, so this
// sketch ships its own partitions.csv (3.75 MB app + 3.25 MB "model"). A
// board flashed with any other scheme has no "model" partition, so we probe
// for it at runtime and fall back to PTT-only voice (touch pad) when absent.
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <math.h>
#include "sdkconfig.h"
#include "ESP_I2S.h"
#include "esp_partition.h"
#include "pins.h"
#include "audio.h"

// Wake word is compile-time gated but ON by default: ESP_SR (wakenet +
// multinet + flite g2p) links well past the 1.25 MB app slot of the stock
// scheme, so the build REQUIRES this sketch's partitions.csv, selected with
// the FQBN option PartitionScheme=custom (see README "Build"). Set to 0 to
// get a small PTT-only image that fits any stock scheme.
#ifndef CLAUDEMICRO_WAKEWORD
#define CLAUDEMICRO_WAKEWORD 1
#endif

#if CLAUDEMICRO_WAKEWORD
// Deliberately NOT behind __has_include: arduino-cli discovers libraries by
// resolving the #include directives it can see, so a header hidden behind a
// failing __has_include is never looked for, ESP_SR never lands on the
// include path, and the guard makes itself true forever (wake word silently
// compiled out). Include it outright and let __has_include below decide.
#include "ESP_SR.h"
#endif
#if CLAUDEMICRO_WAKEWORD && __has_include("ESP_SR.h") && CONFIG_IDF_TARGET_ESP32S3 \
    && (CONFIG_MODEL_IN_FLASH || CONFIG_MODEL_IN_SDCARD)
#define HAVE_ESP_SR 1
#else
#define HAVE_ESP_SR 0
#endif

extern Adafruit_NeoPixel leds;

static I2SClass i2s;
static bool i2sUp = false;
static bool srActive = false;
static volatile bool wakePending = false;

#if HAVE_ESP_SR
// Wake word only - no voice commands on-device (the host owns intent).
static const sr_cmd_t SR_COMMANDS[] = {{0, "Placeholder"}};

static void onSrEvent(sr_event_t event, int, int) {
  // Runs in the SR handler task: just flag it, loop context does the I/O.
  if (event == SR_EVENT_WAKEWORD) wakePending = true;
}

static bool modelPartitionPresent() {
  return esp_partition_find_first(ESP_PARTITION_TYPE_DATA,
                                  ESP_PARTITION_SUBTYPE_ANY, "model") != nullptr;
}
#endif

bool audioBegin() {
  i2s.setPins(PIN_I2S_BCLK, PIN_I2S_WS, PIN_I2S_DOUT, PIN_I2S_DIN);
  i2sUp = i2s.begin(I2S_MODE_STD, 16000, I2S_DATA_BIT_WIDTH_16BIT,
                    I2S_SLOT_MODE_STEREO);
  if (!i2sUp) {
    Serial.println("# audio: I2S init failed");
    return false;
  }
#if HAVE_ESP_SR
  if (modelPartitionPresent()) {
    ESP_SR.onEvent(onSrEvent);
    // Mic on the left slot of a stereo bus -> input format "MN".
    srActive = ESP_SR.begin(i2s, SR_COMMANDS, 0, SR_CHANNELS_STEREO,
                            SR_MODE_WAKEWORD, "MN");
  }
  if (!srActive)
    Serial.println("# audio: no wake-word model partition, PTT-only voice");
#else
  Serial.println("# audio: wake word compiled out (CLAUDEMICRO_WAKEWORD=0), PTT-only voice");
#endif
  return true;
}

bool audioWakeWordActive() { return srActive; }

void audioPoll() {
  if (!wakePending) return;
  wakePending = false;
  Serial.println("W 1");
  // Brief violet flash on the whole deck, then restore host LED state.
  uint32_t saved[NUM_LEDS];
  for (int i = 0; i < NUM_LEDS; i++) saved[i] = leds.getPixelColor(i);
  for (int i = 0; i < NUM_LEDS; i++) leds.setPixelColor(i, leds.Color(60, 20, 80));
  leds.show();
  delay(80);
  for (int i = 0; i < NUM_LEDS; i++) leds.setPixelColor(i, saved[i]);
  leds.show();
}

void audioBeep(int freqHz, int ms) {
  if (!i2sUp || freqHz <= 0) return;
  ms = constrain(ms, 1, 1000);                     // keep the loop responsive
  freqHz = constrain(freqHz, 40, 8000);            // fs/2 = 8 kHz
  constexpr int FRAMES = 128;
  int16_t block[FRAMES * 2];                       // stereo slots
  const float step = 2.0f * (float)M_PI * freqHz / 16000.0f;
  static float phase = 0.0f;
  int frames = 16 * ms;                            // 16 frames per ms @16 kHz
  while (frames > 0) {
    int n = frames < FRAMES ? frames : FRAMES;
    for (int f = 0; f < n; f++) {
      int16_t s = (int16_t)(sinf(phase) * 9000.0f);
      phase += step;
      if (phase > 2.0f * (float)M_PI) phase -= 2.0f * (float)M_PI;
      block[f * 2] = s;                            // left slot
      block[f * 2 + 1] = s;                        // right slot (NS4168)
    }
    i2s.write((uint8_t *)block, n * 4);
    frames -= n;
  }
}

float audioMicRms() {
  // When ESP_SR runs, its feed task owns the RX channel - don't compete.
  if (!i2sUp || srActive) return -1.0f;
  constexpr int FRAMES = 512;                      // 32 ms @16 kHz
  static int16_t buf[FRAMES * 2];
  size_t got = i2s.readBytes((char *)buf, sizeof(buf));
  size_t frames = got / 4;
  if (frames == 0) return -1.0f;
  double acc = 0;
  for (size_t f = 0; f < frames; f++) {            // mic = left slot
    double s = buf[f * 2];
    acc += s * s;
  }
  return (float)sqrt(acc / frames);
}

# AgentDeck V4 firmware

Arduino (ESP32-S3), dual-transport HID: USB when plugged, BLE ("AgentDeckV4")
when on battery. V3 base plus I2S voice (MEMS mic + NS4168 amp), ST7789
240x280 touch LCD (replaces the OLED), and a second EC11. Host protocol is
V3's CDC protocol plus `N <freq> <ms>` (beep), `R` (mic RMS reply) inbound and
`F`/`FS` (ENC2), `TK <n>` (soft-key tap), `W 1` (wake word) outbound - all
additive, so `agentdeck_bridge.py` needs no change (it matches the "AgentDeck"
name substring). See `docs/DESIGN-V4.md` for architecture; `pins.h` mirrors
the generator's PINOUT table (diff them after any hardware change).

## Build (compiles clean; not yet run on hardware)

```
FQBN="esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=enabled,PartitionScheme=custom"
arduino-cli compile --clean --fqbn "$FQBN" v4/firmware/AgentDeckV4
arduino-cli upload  --fqbn "$FQBN" -p /dev/tty.usbmodem* v4/firmware/AgentDeckV4
```
`PartitionScheme=custom` is **required**. The sketch-local `partitions.csv` is
always what ends up in the flashed partition table (the core's
`recipe.hooks.prebuild.3` copies `{sketch}/partitions.csv` over whatever the
menu selected, last writer wins), but `upload.maximum_size` still comes from
the *menu* entry - `1310720` for the default scheme. Without
`PartitionScheme=custom` the link succeeds and then arduino-cli rejects the
image against a 1.25 MB ceiling that no longer describes the flash layout.
`custom` sets that ceiling to 16 MB, so the reported "% of program storage" is
**against 16 MB and is meaningless here** - divide by the real `app0` size
(3,670,016 B) instead. Current image: 1,817,792 B = **49.5 % of app0**.

Libraries: Adafruit NeoPixel, Adafruit GFX Library, "Adafruit ST7735 and
ST7789 Library", NimBLE-Arduino. ESP_I2S and ESP_SR ship with the esp32 core
(3.x); ESP_SR pulls in `libwakenet.a` / `libmultinet.a`.

First flash of a blank board: hold BOOT, tap RESET, release BOOT, then upload
(native USB). After the first flash, auto-reset works.

## Partition layout (custom, 8 MB, no OTA)

`partitions.csv` in this sketch directory. ESP32-S3-WROOM-1-N8R2 = 8 MB flash.

| Name       | Type | SubType  | Offset     | Size            | Notes |
|------------|------|----------|------------|-----------------|-------|
| (bootloader) | -  | -        | `0x0000`   | 32 KB           | table at `0x8000` |
| `nvs`      | data | nvs      | `0x9000`   | 20 KB           | BLE bonds, settings |
| `otadata`  | data | ota      | `0xE000`   | 8 KB            | vestigial; blank -> boot `factory` |
| `app0`     | app  | factory  | `0x10000`  | 3584 KB (3.5 MB)| only app slot |
| `model`    | data | spiffs   | `0x390000` | 3712 KB (3.625 MB) | `srmodels.bin` (3,340,296 B, 88 % full) |
| `spiffs`   | data | spiffs   | `0x730000` | 768 KB          | unused today |
| `coredump` | data | coredump | `0x7F0000` | 64 KB           | panic dumps |

The `model` row copies the **name, type and subtype verbatim** from the core's
`tools/partitions/esp_sr_16.csv` (`model, data, spiffs`) - esp-sr's srmodel
loader looks the partition up by the label `"model"`, so those three fields
are not ours to choose. Only offset and size differ (esp_sr_16 gives it
3968 KB at `0xC10000`, which only exists on 16 MB parts).

**OTA is deliberately unavailable.** A second 3.5 MB app slot does not fit
alongside the model partition in 8 MB, and dropping it is what buys the space.
This board is flashed over native USB, so nothing is lost. `otadata` is kept
(8 KB) because the Arduino upload recipe writes `boot_app0.bin` to `0xE000`
unconditionally; with no `ota_0`/`ota_1` present the bootloader falls through
to `factory`, same as the stock `max_app_8MB` scheme.

Sanity-check a build actually used this table:
```
arduino-cli compile --clean --fqbn "$FQBN" --build-path /tmp/bp v4/firmware/AgentDeckV4
python3 ~/Library/Arduino15/packages/esp32/hardware/esp32/3.3.11/tools/gen_esp32part.py \
        /tmp/bp/AgentDeckV4.ino.partitions.bin
```
That decodes the binary table that will be flashed to `0x8000`; it must list
`app0 3584K` and `model 3712K`. (Verified 2026-07-29 on core 3.3.11.)

### Alternative: boards.local.txt

If you would rather not rely on the sketch-local CSV - or you want
`arduino-cli upload` to flash the model blob for you - add a real menu entry.
Put `partitions.csv` in the core's `tools/partitions/` as
`claudemicro_8MB_sr.csv`, then create
`~/Library/Arduino15/packages/esp32/hardware/esp32/3.3.11/boards.local.txt`:

```
esp32s3.menu.PartitionScheme.cm_sr_8=AgentDeck SR 8M (3.5MB APP/3.6MB MODEL/768KB SPIFFS)
esp32s3.menu.PartitionScheme.cm_sr_8.build.partitions=claudemicro_8MB_sr
esp32s3.menu.PartitionScheme.cm_sr_8.upload.maximum_size=3670016
esp32s3.menu.PartitionScheme.cm_sr_8.upload.extra_flags=0x390000 {build.path}/srmodels.bin
```
Then build with `PartitionScheme=cm_sr_8`. This is strictly better than the
`custom` route: the reported flash % is honest (measured against 3,670,016 B),
and `extra_flags` makes `arduino-cli upload` write `srmodels.bin` to
`0x390000` in the same pass - exactly how the stock `esp_sr_16` entry does it.
The cost is that it lives outside this repo and is lost on a core upgrade.

## Flash the wake-word model (`srmodels.bin`)

**Required.** The app image does not contain the models; without this step the
firmware boots, finds an empty `model` partition, and reports PTT-only voice.

The core ships a prebuilt blob for the S3 (WakeNet9 "Hi ESP" + MultiNet, per
`CONFIG_SR_WN_WN9_HIESP=y` in the core's `sdkconfig`), and copies it into the
build directory whenever ESP_SR is linked
(`recipe.hooks.objcopy.postobjcopy.2`). Both paths are real on this machine:

- source: `~/Library/Arduino15/packages/esp32/tools/esp32s3-libs/3.3.11/esp_sr/srmodels.bin`
- build copy: `{build.path}/srmodels.bin` (3,340,296 B)

Flash it once (it does not change between firmware builds). esptool here is
the v5 binary bundled with the core, named `esptool`, not `esptool.py`:

```
ESPTOOL=~/Library/Arduino15/packages/esp32/tools/esptool_py/5.3.1/esptool
SRMODELS=~/Library/Arduino15/packages/esp32/tools/esp32s3-libs/3.3.11/esp_sr/srmodels.bin
"$ESPTOOL" --chip esp32s3 --port /dev/tty.usbmodem* --baud 921600 \
    --before default-reset --after hard-reset \
    write-flash -z --flash-mode keep --flash-freq keep --flash-size keep \
    0x390000 "$SRMODELS"
```
`0x390000` is the `model` offset from the table above - if you edit
`partitions.csv`, change it here too. On esptool v4 or a pip install the
subcommand is `write_flash` (underscore) instead of `write-flash`.

## Wake word (compiled in; unverified on hardware)

`CLAUDEMICRO_WAKEWORD` defaults to **1** in `audio.cpp`. The build links
ESP_SR (WakeNet9 + MultiNet + flite g2p) and fits the layout above with the
app slot half empty.

Runtime behaviour is unchanged and still defensive: `audioBegin()` probes for
the `model` partition via `esp_partition_find_first(...,"model")` and only
calls `ESP_SR.begin()` if it is there. A board flashed with a stock partition
scheme, or one where step "Flash the wake-word model" was skipped, prints
`# audio: no wake-word model partition, PTT-only voice` and keeps working as a
PTT-only (touch pad) device. Set `CLAUDEMICRO_WAKEWORD` to 0 for a small
PTT-only image (735,963 B) that fits any stock scheme.

One gating fix was needed to make this build at all: the `#include "ESP_SR.h"`
used to sit behind `__has_include("ESP_SR.h")`. arduino-cli discovers
libraries by resolving the `#include` directives it can *see*, so a header
hidden behind a failing `__has_include` is never searched for, ESP_SR never
reaches the include path, and the guard stays false forever - the wake word
silently compiled itself out. The include is now unconditional under
`CLAUDEMICRO_WAKEWORD`; `__has_include` still gates `HAVE_ESP_SR`.

**Still TODO - "hey Claude".** The stock blob only knows "Hi ESP". A custom
wake phrase is not a firmware change: WakeNet models are trained by Espressif
(commercial model-training request via the esp-sr repo / Espressif sales), and
the resulting model has to be packed into a new `srmodels.bin` with esp-sr's
`gen_srmodels`/`pack_model.py` tooling. Nothing in this repo can produce it.

**Nothing here is hardware-verified.** There is no board yet, so "compiles and
the models fit the flash map" is the entire claim. Whether "Hi ESP" is
actually detected through this mic, at this gain, on the left slot of a shared
full-duplex I2S bus is unknown until the smoke test below runs.

## Verify on first hardware (V1 tradition)

- [ ] Matrix orientation: ROW/COL vs physical grid (press K1, check index 0)
- [ ] Diode direction = COL2ROW assumed by scan (rows driven low)
- [ ] LED chain order vs key numbering; GRB color order
- [ ] Touch pad threshold: log `touchRead(PIN_TOUCH)` idle vs pressed
- [ ] VBAT ADC calibration against multimeter at full/half charge
- [ ] BLE pairing from macOS; auto-switch on USB unplug
- [ ] ENC2 direction and switch polarity (`F`/`FS` events on CDC)

LCD:
- [ ] Row offset: `init(240, 280)` applies the 240x280 offset of 20 - confirm
      no 20 px garbage band top/bottom; adjust rotation if the connector ends
      up on the wrong edge
- [ ] Touch presence: boot with the touch module fitted, tap the bottom
      soft-key band, expect `TK 1..4`; a non-touch panel variant must stay
      silent (no ACK at 0x15 -> polled reads disabled)

Audio:
- [ ] Mic sanity: send `R` over CDC, expect `R <rms>` (>0 idle noise floor,
      clearly larger when speaking); only valid while wake word is off
- [ ] Amp beep: send `N 880 200`, expect a clean 880 Hz tone - NS4168
      CTRL=VDD must pick the right slot (mono is duplicated to both)
- [ ] Wake word: boot log must NOT say "no wake-word model partition" - if it
      does, `srmodels.bin` was never flashed to `0x390000` (see above)
- [ ] Wake word smoke test: say "Hi ESP" (not "hey Claude" yet), expect `W 1`
      on CDC + violet LED flash
- [ ] Wake word vs `R`: `audioMicRms()` returns -1 while SR owns the RX
      channel, so the mic-RMS check above is only meaningful with
      `CLAUDEMICRO_WAKEWORD=0`

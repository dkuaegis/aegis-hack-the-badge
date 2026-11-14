#ifdef AEGIS_DOOM

#include <Arduino.h>
#include <LittleFS.h>
#include <U8g2lib.h>
#include <esp_heap_caps.h>
#include <string.h>

#include <DoomGlue.h>
#include <doomgeneric.h>
#include <doomgeneric_fs.h>
#include <palette_esp32.h>
extern "C" {
#include <doomstat.h>
}

#include "doom_badge.h"
#include "doom_music.h"
#include "pins.h"

namespace {
constexpr uint8_t doomMask(DoomButton button) {
  return 1u << static_cast<uint8_t>(button);
}

constexpr uint8_t mapButtons(bool left, bool ok, bool right) {
  return left && right ? doomMask(ok ? DoomButton::Select : DoomButton::Start)
       : left && ok ? doomMask(DoomButton::A)
       : right && ok ? doomMask(DoomButton::B)
       : (left ? doomMask(DoomButton::Left) : 0) |
         (right ? doomMask(DoomButton::Right) : 0) |
         (ok ? doomMask(DoomButton::Up) : 0);
}
static_assert(mapButtons(false, false, false) == 0 &&
              mapButtons(true, false, false) == doomMask(DoomButton::Left) &&
              mapButtons(false, true, false) == doomMask(DoomButton::Up) &&
              mapButtons(false, false, true) == doomMask(DoomButton::Right) &&
              mapButtons(true, true, false) == doomMask(DoomButton::A) &&
              mapButtons(false, true, true) == doomMask(DoomButton::B) &&
              mapButtons(true, false, true) == doomMask(DoomButton::Start) &&
              mapButtons(true, true, true) == doomMask(DoomButton::Select),
              "Three-button Doom controls must cover every chord");

class BadgeDisplay : public IDoomDisplay {
 public:
  U8G2 *oled = nullptr;
  bool begin() override { return true; }
  void beginFrame() override {
    oled->clearBuffer();
    oled->setDrawColor(1);
  }
  void writeRow(int, int, const uint16_t *, int) override {}
  void endFrame() override {
    if (!DG_ScreenBuffer) return;
    static const uint8_t threshold[4][4] = {
        {0, 128, 32, 160}, {192, 64, 224, 96},
        {48, 176, 16, 144}, {240, 112, 208, 80}};
    const int sourceHeight = gamestate == GS_LEVEL ? 168 : 200;
    uint8_t row[128], below[128];
    sampleRow(0, sourceHeight, row);
    sampleRow(1, sourceHeight, below);
    for (int y = 0; y < 64; ++y) {
      for (int x = 0; x < 128; ++x) {
        const int edge = abs(row[x] - row[min(x + 1, 127)]) +
                         abs(row[x] - below[x]);
        const int contrast = min(max((int(row[x]) - 40) * 2, 0), 255);
        if (edge > 35 || contrast > threshold[y & 3][x & 3])
          oled->drawPixel(x, y);
      }
      memcpy(row, below, sizeof(row));
      if (y < 62) sampleRow(y + 2, sourceHeight, below);
    }
    oled->sendBuffer();
  }
  int width() const override { return 128; }
  int height() const override { return 64; }

 private:
  static uint8_t luminance(uint8_t index) {
    const uint16_t pixel = DG_PaletteColor565(index);
    return ((((pixel >> 11) & 31) * 2 + ((pixel >> 5) & 63) * 5 +
             (pixel & 31)) * 255) / 408;
  }
  static void sampleRow(int y, int sourceHeight, uint8_t *row) {
    const int y0 = y * sourceHeight / 64;
    const int y1 = ((y + 1) * sourceHeight - 1) / 64;
    for (int x = 0; x < 128; ++x) {
      const int x0 = x * 320 / 128;
      const int x1 = ((x + 1) * 320 - 1) / 128;
      row[x] = (luminance(DG_ScreenBuffer[y0 * 320 + x0]) +
                luminance(DG_ScreenBuffer[y0 * 320 + x1]) +
                luminance(DG_ScreenBuffer[y1 * 320 + x0]) +
                luminance(DG_ScreenBuffer[y1 * 320 + x1])) / 4;
    }
  }
} display;

class BadgeInput : public IDoomInput {
 public:
  void begin() override {}
  void update() override {
    previous = current;
    const bool left = digitalRead(Pins::BUTTON_LEFT) == LOW;
    const bool right = digitalRead(Pins::BUTTON_RIGHT) == LOW;
    const bool ok = digitalRead(Pins::BUTTON_OK) == LOW;
    current = mapButtons(left, ok, right);
  }
  bool down(DoomButton button) override { return current & doomMask(button); }
  bool pressed(DoomButton button) override {
    return (current & doomMask(button)) && !(previous & doomMask(button));
  }
  bool released(DoomButton button) override {
    return !(current & doomMask(button)) && (previous & doomMask(button));
  }

 private:
  uint8_t current = 0;
  uint8_t previous = 0;
} input;

bool active = false;
} // namespace

const char *doomBegin(U8G2 &oled, void (*tone)(uint16_t)) {
  // The upstream Doom port reserves a 6 MiB zone plus renderer allocations.
  if (!psramFound() ||
      heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM) < 13 * 1024 * 1024 / 2)
    return "DOOM: LOW PSRAM";
  if (!LittleFS.begin(false)) return "DOOM: NO FILESYS";
  File wad = LittleFS.open("/doom1.wad", "r");
  uint8_t header[12];
  if (!wad || wad.size() < 1024 * 1024 || wad.read(header, sizeof(header)) != sizeof(header) ||
      memcmp(header, "IWAD", 4) != 0) {
    wad.close();
    LittleFS.end();
    return "DOOM: WAD MISSING";
  }
  const uint32_t lumps = header[4] | (header[5] << 8) |
                         (header[6] << 16) | (header[7] << 24);
  const uint32_t directory = header[8] | (header[9] << 8) |
                             (header[10] << 16) | (header[11] << 24);
  const bool valid = lumps > 0 && lumps <= 65535 &&
                     static_cast<uint64_t>(directory) + 16ull * lumps <= wad.size();
  wad.close();
  if (!valid) {
    LittleFS.end();
    return "DOOM: INVALID WAD";
  }

  display.oled = &oled;
  input.begin();
  DG_FS = &LittleFS;
  DG_Display = &display;
  DG_Input = &input;
  doomMusicUseTone(tone);
  static char wadArg[] = "/doom1.wad";
  static char *args[] = {(char *)"doom", (char *)"-iwad", wadArg,
                         (char *)"-warp", (char *)"1", (char *)"1",
                         (char *)"-mb", (char *)"6"};
  doomgeneric_Create(8, args);
  active = true;
  return nullptr;
}

void doomTick() {
  if (active) DoomGlue_Tick();
}

void doomEnd() {
  if (!active) return;
  DoomGlue_Shutdown();
  DG_Input = nullptr;
  DG_Display = nullptr;
  DG_FS = nullptr;
  doomMusicUseTone(nullptr);
  LittleFS.end();
  active = false;
}

bool doomRunning() { return active; }
#endif

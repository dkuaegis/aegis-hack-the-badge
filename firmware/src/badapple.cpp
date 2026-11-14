#ifdef AEGIS_BADAPPLE

#include <Arduino.h>
#include <LittleFS.h>
#include <U8g2lib.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <math.h>
#include <string.h>

#include "badapple.h"
#include "logic.h"

namespace {
constexpr uint32_t FRAME_COUNT = 6573;
constexpr uint32_t FPS = 30;
constexpr uint32_t DURATION_MS = FRAME_COUNT * 1000 / FPS;
constexpr uint16_t SYNC_MAGIC = 0xba11;
constexpr uint8_t SYNC_VERSION = 1;
constexpr uint8_t BROADCAST[6] = {255, 255, 255, 255, 255, 255};

struct __attribute__((packed)) SyncPacket {
  uint16_t magic;
  uint8_t version;
  uint8_t reserved;
  int32_t untilStartMs;
  uint32_t frames;
};
static_assert(sizeof(SyncPacket) == 12, "Bad Apple sync packet");

struct ReceivedSync {
  SyncPacket packet;
  uint32_t sender;
};

enum class Mode : uint8_t { Solo, Lead, Harmony, Bass };
enum class State : uint8_t { Select, Waiting, Playing, Error };

U8G2 *display = nullptr;
void (*toneOutput)(uint16_t) = nullptr;
File video, music;
QueueHandle_t syncQueue = nullptr;
bool active = false, radioReady = false;
Mode mode = Mode::Solo;
State state = State::Select;
uint32_t startAt = 0, sentAt = 0, leaderId = 0;
uint32_t nextFrame = 0;
uint8_t frame[1024], fileBuffer[512];
size_t filePos = 0, fileLength = 0;
uint16_t runRemaining = 0;
uint8_t runValue = 0;
uint32_t counts[3], offsets[3], notesLeft = 0, nextNoteAt = 0;
uint8_t nextNote = 0, sounding = 0;

void drawText(const char *line1, const char *line2, const char *line3) {
  display->clearBuffer();
  display->setFont(u8g2_font_6x10_tf);
  display->drawStr(0, 12, "BAD APPLE!!");
  display->drawHLine(0, 16, 128);
  display->drawStr(0, 32, line1);
  display->drawStr(0, 45, line2);
  display->setFont(u8g2_font_5x7_tf);
  display->drawStr(0, 62, line3);
  display->sendBuffer();
}

void drawSelect() {
  static const char *names[] = {"SOLO", "LEAD / MELODY", "JOIN / HARMONY", "JOIN / BASS"};
  drawText(names[static_cast<uint8_t>(mode)],
           mode == Mode::Solo ? "ONE BADGE" : "ESP-NOW CH 1",
           "L/R: MODE  OK: PLAY");
}

void stopTone() {
  sounding = 0;
  if (toneOutput) toneOutput(0);
}

uint16_t frequency(uint8_t note) {
  float hz = 440.0f * powf(2.0f, (static_cast<int>(note) - 69) / 12.0f);
  // shortcut: one passive buzzer plays one part; add a speaker for recorded audio.
  while (hz < 440) hz *= 2;
  while (hz > 2500) hz *= 0.5f;
  return static_cast<uint16_t>(hz);
}

bool readMusicEvent() {
  if (!notesLeft) return false;
  uint8_t raw[5];
  if (music.read(raw, sizeof(raw)) != sizeof(raw)) {
    state = State::Error;
    stopTone();
    drawText("MUSIC READ ERROR", "", "HOLD L+R: HOME");
    return false;
  }
  nextNoteAt = static_cast<uint32_t>(raw[0]) | (static_cast<uint32_t>(raw[1]) << 8) |
               (static_cast<uint32_t>(raw[2]) << 16) | (static_cast<uint32_t>(raw[3]) << 24);
  nextNote = raw[4];
  --notesLeft;
  return true;
}

void pollMusic(uint32_t elapsed) {
  for (int processed = 0; state == State::Playing && nextNoteAt <= elapsed &&
                          processed < 64; ++processed) {
    if (nextNote != sounding) {
      sounding = nextNote;
      if (toneOutput) toneOutput(sounding ? frequency(sounding) : 0);
    }
    if (!readMusicEvent()) {
      nextNoteAt = UINT32_MAX;
      break;
    }
  }
}

bool readVideoByte(uint8_t &value) {
  if (filePos == fileLength) {
    fileLength = video.read(fileBuffer, sizeof(fileBuffer));
    filePos = 0;
    if (!fileLength) return false;
  }
  value = fileBuffer[filePos++];
  return true;
}

uint8_t reverseBits(uint8_t value) {
  value = ((value & 0xf0) >> 4) | ((value & 0x0f) << 4);
  value = ((value & 0xcc) >> 2) | ((value & 0x33) << 2);
  return ((value & 0xaa) >> 1) | ((value & 0x55) << 1);
}

bool decodeFrame() {
  for (size_t filled = 0; filled < sizeof(frame);) {
    if (!runRemaining) {
      uint8_t code, count;
      if (!readVideoByte(code)) return false;
      runValue = code;
      runRemaining = 1;
      if (code == 0x55 || code == 0xaa) {
        if (!readVideoByte(count)) return false;
        if (count != 0) {
          runRemaining = count;
          if (count & 0x80) {
            uint8_t high;
            if (!readVideoByte(high)) return false;
            runRemaining = (count & 0x7f) | (static_cast<uint16_t>(high) << 7);
          }
          if (!runRemaining) return false;
          runValue = code == 0x55 ? 0 : 255;
        }
      }
    }
    const size_t take = min<size_t>(runRemaining, sizeof(frame) - filled);
    memset(frame + filled, reverseBits(runValue), take);
    filled += take;
    runRemaining -= take;
  }
  return true;
}

void renderFrame() {
  display->clearBuffer();
  display->drawXBM(0, 0, 128, 64, frame);
  display->sendBuffer();
}

void receiveSync(const uint8_t *mac, const uint8_t *data, int length) {
  if (!mac || !syncQueue || length != sizeof(SyncPacket)) return;
  ReceivedSync received{};
  memcpy(&received.packet, data, sizeof(SyncPacket));
  if (received.packet.magic != SYNC_MAGIC || received.packet.version != SYNC_VERSION ||
      received.packet.frames != FRAME_COUNT) return;
  received.sender = macSuffix24(mac);
  xQueueSend(syncQueue, &received, 0);
}

void stopRadio() {
  if (radioReady) {
    esp_now_unregister_recv_cb();
    esp_now_deinit();
  }
  radioReady = false;
  if (syncQueue) {
    vQueueDelete(syncQueue);
    syncQueue = nullptr;
  }
  WiFi.mode(WIFI_OFF);
}

bool startRadio() {
  syncQueue = xQueueCreate(8, sizeof(ReceivedSync));
  if (!syncQueue) return false;
  WiFi.mode(WIFI_STA);
  if (esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE) != ESP_OK ||
      esp_now_init() != ESP_OK) {
    stopRadio();
    return false;
  }
  radioReady = true;
  if (esp_now_register_recv_cb(receiveSync) != ESP_OK) {
    stopRadio();
    return false;
  }
  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, BROADCAST, sizeof(BROADCAST));
  peer.ifidx = WIFI_IF_STA;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    stopRadio();
    return false;
  }
  return true;
}

void sendSync(uint32_t now) {
  if (!radioReady) return;
  const SyncPacket packet{SYNC_MAGIC, SYNC_VERSION, 0,
                          static_cast<int32_t>(startAt - now), FRAME_COUNT};
  esp_now_send(BROADCAST, reinterpret_cast<const uint8_t *>(&packet), sizeof(packet));
  sentAt = now;
}

bool startPlayback(uint32_t at) {
  if (!video.seek(0)) return false;
  const uint8_t part = mode == Mode::Harmony ? 1 : mode == Mode::Bass ? 2 : 0;
  if (!music.seek(offsets[part])) return false;
  filePos = fileLength = 0;
  runRemaining = 0;
  nextFrame = 0;
  notesLeft = counts[part];
  nextNoteAt = UINT32_MAX;
  stopTone();
  if (!readMusicEvent()) return false;
  startAt = at;
  state = State::Playing;
  drawText("READY", mode == Mode::Solo ? "SOLO" : "SYNCED",
           "HOLD L+R: HOME");
  return true;
}

void finish() {
  stopTone();
  stopRadio();
  state = State::Select;
  mode = Mode::Solo;
  drawSelect();
}
} // namespace

const char *badAppleBegin(U8G2 &oled, void (*tone)(uint16_t)) {
  if (!LittleFS.begin(false)) return "BAD APPLE: NO FS";
  video = LittleFS.open("/video.rle", "r");
  music = LittleFS.open("/music.bin", "r");
  uint8_t header[32];
  if (!video || video.size() < 100000 || !music ||
      music.read(header, sizeof(header)) != sizeof(header) ||
      memcmp(header, "BAM1", 4) != 0) {
    video.close(); music.close(); LittleFS.end();
    return "BAD APPLE: NO DATA";
  }
  const uint32_t duration = static_cast<uint32_t>(header[4]) |
      (static_cast<uint32_t>(header[5]) << 8) |
      (static_cast<uint32_t>(header[6]) << 16) |
      (static_cast<uint32_t>(header[7]) << 24);
  for (int i = 0; i < 3; ++i) {
    const int c = 8 + i * 4, o = 20 + i * 4;
    counts[i] = static_cast<uint32_t>(header[c]) |
                (static_cast<uint32_t>(header[c + 1]) << 8) |
                (static_cast<uint32_t>(header[c + 2]) << 16) |
                (static_cast<uint32_t>(header[c + 3]) << 24);
    offsets[i] = static_cast<uint32_t>(header[o]) |
                 (static_cast<uint32_t>(header[o + 1]) << 8) |
                 (static_cast<uint32_t>(header[o + 2]) << 16) |
                 (static_cast<uint32_t>(header[o + 3]) << 24);
  }
  bool valid = duration == DURATION_MS && offsets[0] == sizeof(header);
  for (int i = 0; i < 3; ++i)
    valid &= counts[i] > 0 && counts[i] <= (music.size() - min<size_t>(offsets[i], music.size())) / 5 &&
             offsets[i] <= music.size() &&
             (i == 2 ? offsets[i] + counts[i] * 5 == music.size()
                     : offsets[i] + counts[i] * 5 == offsets[i + 1]);
  if (!valid) {
    video.close(); music.close(); LittleFS.end();
    return "BAD APPLE: BAD DATA";
  }
  display = &oled;
  toneOutput = tone;
  mode = Mode::Solo;
  state = State::Select;
  active = true;
  drawSelect();
  return nullptr;
}

void badAppleTick(uint32_t now, bool leftPressed, bool okPressed,
                  bool rightPressed, bool exitChord) {
  if (!active) return;
  if (state == State::Select) {
    if (exitChord) return;
    if (leftPressed || rightPressed) {
      mode = static_cast<Mode>((static_cast<uint8_t>(mode) + (leftPressed ? 3 : 1)) % 4);
      drawSelect();
    } else if (okPressed) {
      if (mode != Mode::Solo && !startRadio()) {
        drawText("RADIO ERROR", "CHECK CH 1", "L/R: MODE  OK: RETRY");
      } else if (mode == Mode::Harmony || mode == Mode::Bass) {
        leaderId = 0;
        state = State::Waiting;
        drawText("WAITING FOR LEAD", mode == Mode::Harmony ? "HARMONY" : "BASS",
                 "HOLD L+R: HOME");
      } else if (!startPlayback(now + (mode == Mode::Lead ? 2000 : 0))) {
        state = State::Error;
        drawText("DATA READ ERROR", "", "HOLD L+R: HOME");
      } else if (mode == Mode::Lead) sendSync(now);
    }
    return;
  }
  if (state == State::Error) return;

  ReceivedSync received{};
  while (syncQueue && xQueueReceive(syncQueue, &received, 0) == pdTRUE) {
    if (mode == Mode::Lead ||
        (leaderId && leaderId != received.sender)) continue;
    if (state == State::Waiting && received.packet.untilStartMs > 0 &&
        received.packet.untilStartMs <= 3000) {
      leaderId = received.sender;
      if (!startPlayback(now + received.packet.untilStartMs)) {
        state = State::Error;
        drawText("DATA READ ERROR", "", "HOLD L+R: HOME");
      }
    } else if (state == State::Playing && mode != Mode::Solo) {
      const uint32_t wanted = now + received.packet.untilStartMs;
      if (abs(static_cast<int32_t>(wanted - startAt)) > 25) startAt = wanted;
    }
  }
  if (state != State::Playing) return;
  if (mode == Mode::Lead && (sentAt == 0 || now - sentAt >=
       (static_cast<int32_t>(startAt - now) > 0 ? 100u : 5000u))) sendSync(now);
  if (static_cast<int32_t>(now - startAt) < 0) return;
  const uint32_t elapsed = now - startAt;
  if (elapsed >= DURATION_MS) { finish(); return; }
  pollMusic(elapsed);
  const uint32_t target = elapsed * FPS / 1000;
  for (int decoded = 0; nextFrame <= target && decoded < 4; ++decoded) {
    if (!decodeFrame()) {
      state = State::Error;
      stopTone();
      drawText("VIDEO READ ERROR", "", "HOLD L+R: HOME");
      return;
    }
    if (nextFrame == target) renderFrame();
    ++nextFrame;
  }
}

void badAppleEnd() {
  if (!active) return;
  stopTone();
  stopRadio();
  video.close();
  music.close();
  LittleFS.end();
  display = nullptr;
  toneOutput = nullptr;
  active = false;
}

bool badAppleRunning() { return active; }
#endif

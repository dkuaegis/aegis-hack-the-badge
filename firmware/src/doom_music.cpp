#ifdef AEGIS_DOOM

#include <Arduino.h>
#include <math.h>
#include <string.h>

extern "C" {
#include <i_sound.h>
}

#include "doom_music.h"

namespace {
const uint8_t *score = nullptr;
uint32_t start = 0, end = 0, position = 0, nextAt = 0;
uint32_t pausedAt = 0;
int8_t leadNote = -1;
int volume = 127;
uint16_t sounding = 0;
bool playing = false, paused = false, looping = false;
void (*toneOutput)(uint16_t) = nullptr;

void updateTone() {
  uint16_t frequency = 0;
  if (playing && !paused && volume && leadNote >= 0) {
    float hz = 440.0f * powf(2.0f, (leadNote - 69) / 12.0f);
    // shortcut: one PWM tone follows MUS channel 0; use a speaker for full polyphony.
    while (hz < 550) hz *= 2;
    while (hz > 3500) hz *= 0.5f;
    frequency = static_cast<uint16_t>(hz);
  }
  if (frequency != sounding) {
    sounding = frequency;
    if (toneOutput) toneOutput(frequency);
  }
}

void stop() {
  playing = false;
  leadNote = -1;
  updateTone();
}

bool readByte(uint8_t &value) {
  if (!score || position >= end) { stop(); return false; }
  value = score[position++];
  return true;
}

bool nextGroup(uint32_t &delay) {
  for (int events = 0; events < 64; ++events) {
    uint8_t event;
    if (!readByte(event)) return false;
    const uint8_t kind = (event >> 4) & 7;
    const uint8_t channel = event & 15;
    uint8_t note = 0, value = 0;
    switch (kind) {
      case 0: // note off
        if (!readByte(note)) return false;
        if (channel == 0 && leadNote == (note & 127)) leadNote = -1;
        break;
      case 1: // note on, optionally followed by velocity
        if (!readByte(note)) return false;
        if (note & 128) {
          if (!readByte(value)) return false;
        } else {
          value = 100;
        }
        if (channel == 0) leadNote = value ? (note & 127) : -1;
        break;
      case 2: case 3: case 7:
        if (!readByte(value)) return false;
        break;
      case 4:
        if (!readByte(value) || !readByte(value)) return false;
        break;
      case 5:
        break;
      case 6:
        if (!looping) { stop(); return false; }
        position = start;
        leadNote = -1;
        delay = 1;
        return true;
    }
    if (event & 128) {
      delay = 0;
      for (int bytes = 0; bytes < 5; ++bytes) {
        if (!readByte(value)) return false;
        delay = (delay << 7) | (value & 127);
        if (!(value & 128)) return true;
      }
      stop();
      return false;
    }
  }
  stop();
  return false;
}

doom_boolean init() { return true; }
void shutdown() { stop(); score = nullptr; }
void setVolume(int value) {
  volume = value < 0 ? 0 : value > 127 ? 127 : value;
  updateTone();
}
void pause() { pausedAt = micros(); paused = true; updateTone(); }
void resume() {
  if (paused) nextAt += micros() - pausedAt;
  paused = false;
  updateTone();
}
void *registerSong(void *data, int length) {
  const uint8_t *bytes = static_cast<const uint8_t *>(data);
  if (!bytes || length < 16 || memcmp(bytes, "MUS\x1a", 4) != 0) return nullptr;
  const uint32_t size = bytes[4] | (bytes[5] << 8);
  const uint32_t offset = bytes[6] | (bytes[7] << 8);
  if (offset < 16 || size == 0 || offset + size > static_cast<uint32_t>(length))
    return nullptr;
  score = bytes;
  start = offset;
  end = offset + size;
  return data;
}
void unregisterSong(void *handle) {
  if (handle == score) { stop(); score = nullptr; }
}
void playSong(void *handle, doom_boolean repeat) {
  if (!score || handle != score) return;
  position = start;
  leadNote = -1;
  looping = repeat;
  paused = false;
  playing = true;
  nextAt = micros();
  updateTone();
}
doom_boolean isPlaying() { return playing; }
void poll() {
  if (!playing || paused) return;
  const uint32_t now = micros();
  int groups = 0;
  while (playing && static_cast<int32_t>(now - nextAt) >= 0 && groups++ < 32) {
    uint32_t delay = 0;
    if (!nextGroup(delay)) break;
    updateTone();
    nextAt += max<uint32_t>(delay, 1) * 1000000u / 140u;
  }
  if (groups >= 32) nextAt = now + 1000000u / 140u;
  updateTone();
}

snddevice_t devices[] = {SNDDEVICE_SB};
} // namespace

void doomMusicUseTone(void (*tone)(uint16_t)) { toneOutput = tone; }

extern "C" {
music_module_t badge_music_module = {
    devices, 1, init, shutdown, setVolume, pause, resume, registerSong,
    unregisterSong, playSong, stop, isPlaying, poll};
}
#endif

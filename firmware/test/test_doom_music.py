"""Exercise the badge's MUS-to-buzzer path without ESP32 hardware."""

import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
arduino_stub = r'''
#pragma once
#include <stdint.h>
extern uint32_t fakeMicros;
inline uint32_t micros() { return fakeMicros; }
template <typename T> constexpr T max(T a, T b) { return a > b ? a : b; }
'''
sound_stub = r'''
#pragma once
typedef int doom_boolean;
typedef enum { SNDDEVICE_SB = 1 } snddevice_t;
typedef struct {
  snddevice_t *devices;
  int count;
  doom_boolean (*Init)();
  void (*Shutdown)();
  void (*SetMusicVolume)(int);
  void (*PauseMusic)();
  void (*ResumeMusic)();
  void *(*RegisterSong)(void *, int);
  void (*UnRegisterSong)(void *);
  void (*PlaySong)(void *, doom_boolean);
  void (*StopSong)();
  doom_boolean (*MusicIsPlaying)();
  void (*Poll)();
} music_module_t;
'''
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <vector>
#include "doom_music.h"
#include <i_sound.h>
extern "C" music_module_t badge_music_module;
uint32_t fakeMicros = 0;
std::vector<uint16_t> tones;
void output(uint16_t frequency) { tones.push_back(frequency); }
int main() {
  unsigned char song[] = {
      'M','U','S',26, 8,0, 16,0, 0,0,0,0,0,0,0,0,
      0x90,0xa8,100,20, 0x80,40,5, 0x60};
  auto &music = badge_music_module;
  doomMusicUseTone(output);
  assert(music.Init());
  assert(music.RegisterSong(song, sizeof(song)) == song);
  music.PlaySong(song, false);
  music.Poll();
  assert(tones.size() == 1 && tones.back() >= 550 && tones.back() <= 700);
  fakeMicros = 10000;
  music.PauseMusic();
  assert(tones.back() == 0);
  fakeMicros = 1010000;
  music.ResumeMusic();
  assert(tones.back() >= 550);
  fakeMicros = 1143000;
  music.Poll();
  assert(tones.back() == 0);
  fakeMicros = 1180000;
  music.Poll();
  assert(!music.MusicIsPlaying());
  music.UnRegisterSong(song);
  song[0] = 'X';
  assert(music.RegisterSong(song, sizeof(song)) == nullptr);
  music.Shutdown();
}
'''

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    (work / "Arduino.h").write_text(arduino_stub)
    (work / "i_sound.h").write_text(sound_stub)
    (work / "test.cpp").write_text(harness)
    binary = work / "test_doom_music"
    subprocess.run([
        os.environ.get("CXX", "clang++"), "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-DAEGIS_DOOM", f"-I{work}", f"-I{root / 'src'}",
        str(root / "src/doom_music.cpp"), str(work / "test.cpp"), "-o", str(binary),
    ], check=True)
    subprocess.run([str(binary)], check=True)
print("Doom MUS buzzer sequencer: OK")

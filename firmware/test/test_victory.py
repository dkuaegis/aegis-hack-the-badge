"""Compile the real completion handlers with host Serial/UI stubs."""

import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "src/main.cpp").read_text()


def extract(start, end):
    return start + source.split(start, 1)[1].split(end, 1)[0]


harness = r'''
#include <assert.h>
#include <string>
#include "logic.h"
#include "problems.h"
#define F(value) value
#define BADGE_FINAL_FLAG "TEST_ONLY_FINAL_FLAG"
std::string output;
struct { void println(const char *s) { output += s; output += '\n'; } } Serial;
uint8_t solvedMask = 0;
uint32_t now = 100, hiddenVictoryAt = 0;
uint32_t millis() { return now; }
enum class PlayerTarget { Usb, Ble };
enum class Screen { Status, HiddenGranted, Complete };
enum class VictoryPhase { FlashOn1 };
struct VictoryState {
  bool active = false;
  VictoryPhase phase = VictoryPhase::FlashOn1;
  uint32_t nextAt = 0;
} victory;
Screen screen = Screen::Status;
int usbPlayer = 0, blePlayer = 0;
int &playerContext(PlayerTarget target) { return target == PlayerTarget::Usb ? usbPlayer : blePlayer; }
bool bleStatusDirty = false, ledsOn = false, hiddenEvent = false;
unsigned completeDraws = 0;
void resetPlayer(int &) {}
void drawComplete() { ++completeDraws; }
void setAllStatusLeds(bool on) { ledsOn = on; }
void saveMask() {}
void playerPrintf(PlayerTarget, const char *, ...) {}
uint8_t serialSolvedCount() { return 4; }
void beep(int, int) {}
void drawStatus() {}
void pollSerial() {}
void updateBleAdmin(uint32_t) {}
void updateUi(uint32_t) {}
void updateMorseRadio(uint32_t) {}
void updateBuzzer(uint32_t) {}
void updateVictory(uint32_t) {}
void updateTrophyLedSweep(uint32_t) {}
void drawHiddenGranted() {}
void delay(int) {}
bool updateHiddenAccess(uint32_t) {
  if (!hiddenEvent) return false;
  hiddenEvent = false;
  solvedMask = markSolved(solvedMask, HIDDEN_ACCESS_INDEX);
  return true;
}
'''
harness += extract("bool allSolved() {", "\nvoid updateProgressLeds")
harness += extract("void printVictoryMessage() {", "\nvoid updateVictory")
harness += extract("void finishProblem(", "\nvoid incorrect")
harness += extract("void loop() {", "\n// END OF FILE")
harness += r'''
void assertVictory() {
  assert(output.find("Congratulations!") != std::string::npos);
  assert(output.find("  ____") != std::string::npos);
  assert(output.find("AEGIS{PWN3D!}") != std::string::npos);
  assert(output.find(BADGE_FINAL_FLAG) != std::string::npos);
  assert(screen == Screen::Complete && victory.active && ledsOn && bleStatusDirty);
  assert(completeDraws > 0 && victory.nextAt == now + 250);
}
int main() {
  for (uint8_t mask = 0; mask < 32; ++mask) {
    solvedMask = mask;
    assert(allSolved() == (mask == 31));
  }
  solvedMask = 0;
  for (uint8_t i = 0; i < SERIAL_PROBLEM_COUNT; ++i) finishProblem(PlayerTarget::Usb, i);
  assert(output.empty()); // Four serial missions alone never reveal the final flag.
  hiddenEvent = true;
  loop();
  assert(output.empty() && hiddenVictoryAt == now + 750);
  now += 749;
  loop();
  assert(output.empty());
  ++now;
  loop();
  assertVictory(); // Hidden solved last preserves the granted screen delay.
  const auto first = output;
  finishProblem(PlayerTarget::Usb, 3);
  loop();
  assert(output == first); // Re-submission must not restart the celebration.
  output.clear();
  solvedMask = solvedBit(HIDDEN_ACCESS_INDEX);
  for (uint8_t i = 0; i < SERIAL_PROBLEM_COUNT; ++i) {
    finishProblem(PlayerTarget::Usb, i);
    if (i < 3) assert(output.empty());
  }
  assertVictory(); // Hidden solved first also waits for the fourth serial mission.
  output.clear();
  startVictorySequence(now); // Completed badges replay the same message at boot.
  assertVictory();
}
'''
with tempfile.TemporaryDirectory() as directory:
    cpp = Path(directory) / "victory.cpp"
    binary = Path(directory) / "victory"
    cpp.write_text(harness)
    subprocess.run([os.environ.get("CXX", "clang++"), "-std=c++17",
                    "-Wall", "-Wextra", "-Werror", f"-I{root / 'src'}",
                    str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("five-challenge gate, both solve orders, celebration and final flag: OK")

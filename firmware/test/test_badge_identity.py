"""Run the firmware's NVS number load/save functions with a storage stub."""

import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "src/main.cpp").read_text()
handlers = "bool setBadgeNumber(" + source.split("bool setBadgeNumber(", 1)[1].split(
    "\nvoid drawBootFrame", 1)[0]
harness = r'''
#include <assert.h>
#include <string.h>
#include "badge_identity.h"
#include "logic.h"
#define BADGE_NUMBER 1
struct {
  bool exists = false, fail = false;
  uint16_t number = 0;
  unsigned writes = 0;
  bool isKey(const char *) { return exists; }
  uint16_t getUShort(const char *, uint16_t fallback) { return exists ? number : fallback; }
  size_t putUShort(const char *, uint16_t value) {
    ++writes;
    if (fail) return 0;
    exists = true;
    number = value;
    return sizeof(value);
  }
} preferences;
struct { void println(const char *) {} } Serial;
uint16_t badgeNumber = 0;
char badgeLabel[19];
uint8_t deviceMac[] = {0xaa, 0xbb, 0xcc, 0x11, 0x22, 0x33};
'''
harness += handlers + r'''
int main() {
  loadBadgeIdentity();
  assert(badgeNumber == 1 && preferences.number == 1 && preferences.writes == 1);
  assert(strcmp(badgeLabel, "BADGE #01") == 0);
  assert(setBadgeNumber(42));
  badgeNumber = 0;
  loadBadgeIdentity(); // Reboot loads NVS instead of overwriting with build seed 1.
  assert(badgeNumber == 42 && strcmp(badgeLabel, "BADGE #42") == 0);
  assert(preferences.writes == 2);
  assert(!setBadgeNumber(1000) && !setBadgeNumber(BADGE_NUMBER_ADMIN));
  assert(badgeNumber == 42 && preferences.writes == 2);
  preferences.fail = true;
  assert(!setBadgeNumber(2) && badgeNumber == 42 && preferences.number == 42);
  assert(strcmp(badgeLabel, "BADGE #42") == 0);
  preferences.fail = false;
  assert(setBadgeNumber(0));
  loadBadgeIdentity();
  assert(badgeNumber == 0 && strcmp(badgeLabel, "AEGIS-112233") == 0);
  assert(macSuffix24(deviceMac) == 0x112233); // Label changes never alter the ID.
  preferences.exists = false;
  preferences.fail = true;
  loadBadgeIdentity();
  assert(badgeNumber == 0 && strcmp(badgeLabel, "AEGIS-112233") == 0);
}
'''
with tempfile.TemporaryDirectory() as directory:
    cpp = Path(directory) / "badge_identity.cpp"
    binary = Path(directory) / "badge_identity"
    cpp.write_text(harness)
    subprocess.run([os.environ.get("CXX", "clang++"), "-std=c++17",
                    "-Wall", "-Wextra", "-Werror", f"-I{root / 'src'}",
                    str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("badge number NVS seed, persistence, validation and write failure tests: OK")

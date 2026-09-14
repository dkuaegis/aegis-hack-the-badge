"""Run the adapter's LED handlers with a fake clock and RGB output."""

import os
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / "src/morse_adapter.cpp").read_text()
handlers = "constexpr uint8_t MORSE_LED_PIN" + source.split(
    "constexpr uint8_t MORSE_LED_PIN", 1)[1].split("\nvoid receivePacket", 1)[0]
harness = r'''
#include <assert.h>
#include <stdint.h>
uint32_t now = 0;
uint32_t millis() { return now; }
uint8_t red = 0, blue = 0;
unsigned writes = 0;
void neopixelWrite(uint8_t pin, uint8_t r, uint8_t g, uint8_t b) {
  assert(pin == 38 && g == 0);
  red = r;
  blue = b;
  ++writes;
}
'''
harness += handlers + r'''
int main() {
  updateActivityLed();
  showActivityLed(true, 0);
  assert(writes == 0); // Idle and boundary packets leave the LED off.
  showActivityLed(true, 100);
  assert(red == MORSE_LED_BRIGHTNESS && blue == 0);
  now = 99;
  updateActivityLed();
  assert(red != 0 && writes == 1);
  now = 100;
  updateActivityLed();
  assert(red == 0 && blue == 0 && !activityLit);
  showActivityLed(true, 300);
  now = 150;
  showActivityLed(false, 100); // Latest RX replaces an active TX indication.
  assert(red == 0 && blue == MORSE_LED_BRIGHTNESS);
  showActivityLed(true, 0); // A boundary cannot override the active RX pulse.
  assert(red == 0 && blue != 0 && activityUntil == 250);
  now = 250;
  updateActivityLed();
  assert(red == 0 && blue == 0);
  now = UINT32_MAX - 99;
  showActivityLed(false, 300);
  now = 199;
  updateActivityLed();
  assert(blue != 0); // millis() rollover must not end the pulse early.
  now = 200;
  updateActivityLed();
  assert(red == 0 && blue == 0);
}
'''
with tempfile.TemporaryDirectory() as directory:
    cpp = Path(directory) / "morse_led.cpp"
    binary = Path(directory) / "morse_led"
    cpp.write_text(harness)
    subprocess.run([os.environ.get("CXX", "clang++"), "-std=c++17",
                    "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("Morse LED TX/RX, timeout and clock rollover tests: OK")

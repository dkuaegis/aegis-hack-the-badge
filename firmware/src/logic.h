#pragma once

#include <stdint.h>

constexpr uint8_t solvedBit(uint8_t index) {
  return static_cast<uint8_t>(1U << index);
}

constexpr bool isSolved(uint8_t mask, uint8_t index) {
  return (mask & solvedBit(index)) != 0;
}

constexpr uint8_t markSolved(uint8_t mask, uint8_t index) {
  return static_cast<uint8_t>(mask | solvedBit(index));
}

constexpr uint8_t solvedMaskFor(uint8_t count) {
  return count >= 8 ? 0xff : static_cast<uint8_t>((1U << count) - 1U);
}

constexpr uint16_t legacyAuthResponse(uint16_t challenge, uint16_t key) {
  return static_cast<uint16_t>(challenge ^ key);
}

inline bool parseHex16(const char *text, uint16_t &value) {
  if (text == nullptr) return false;
  uint16_t parsed = 0;
  for (uint8_t i = 0; i < 4; ++i) {
    const char c = text[i];
    uint8_t digit = 0;
    if (c >= '0' && c <= '9') digit = c - '0';
    else if (c >= 'a' && c <= 'f') digit = c - 'a' + 10;
    else if (c >= 'A' && c <= 'F') digit = c - 'A' + 10;
    else return false;
    parsed = static_cast<uint16_t>((parsed << 4) | digit);
  }
  if (text[4] != '\0') return false;
  value = parsed;
  return true;
}

// C0 is only ever driven LOW. The intended solution is C0-C2, with C1 open.
constexpr bool hiddenAccessMatched(bool challenge1Low, bool challenge2Low) {
  return !challenge1Low && challenge2Low;
}

constexpr bool flappyCollision(float birdY, float pipeX, int gapY) {
  return birdY <= 0 || birdY + 6 >= 64 ||
         (pipeX < 35 && pipeX + 11 > 28 &&
          (birdY < gapY - 13 || birdY + 6 > gapY + 13));
}

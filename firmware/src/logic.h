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

constexpr bool rectsOverlap(float ax, float ay, float aw, float ah,
                            float bx, float by, float bw, float bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

inline char decodeMorse(uint8_t bits, uint8_t length) {
  static const char one[] = "ET";
  static const char two[] = "IANM";
  static const char three[] = "SURWDKGO";
  static const char four[] = "HVF?L?PJ" "BXCYZQ??";
  if (length == 1) return one[bits];
  if (length == 2) return two[bits];
  if (length == 3) return three[bits];
  if (length == 4) return four[bits];
  if (length == 5) {
    switch (bits) {
      case 0: return '5';
      case 1: return '4';
      case 3: return '3';
      case 7: return '2';
      case 15: return '1';
      case 16: return '6';
      case 24: return '7';
      case 28: return '8';
      case 30: return '9';
      case 31: return '0';
    }
  }
  return '?';
}

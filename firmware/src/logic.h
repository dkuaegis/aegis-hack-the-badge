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

inline char stepLeaderboardChar(char current, int8_t direction) {
  static constexpr char characters[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  uint8_t index = 0;
  while (characters[index] != '\0' && characters[index] != current) ++index;
  if (characters[index] == '\0') index = 0;
  return characters[(index + (direction < 0 ? 35 : 1)) % 36];
}

inline bool validLeaderboardName(const char *name, uint8_t maxLength) {
  if (name == nullptr || maxLength == 0) return false;
  uint8_t length = 0;
  while (length <= maxLength && name[length] != '\0') ++length;
  if (length == 0 || length > maxLength) return false;
  for (uint8_t i = 0; i < length; ++i) {
    if (!((name[i] >= 'A' && name[i] <= 'Z') ||
          (name[i] >= '0' && name[i] <= '9'))) return false;
  }
  return true;
}

inline uint8_t clearFullRows(uint16_t *rows, uint8_t height,
                             uint16_t fullMask) {
  if (rows == nullptr || height == 0) return 0;
  uint8_t cleared = 0;
  for (int16_t read = height - 1, write = height - 1; read >= 0; --read) {
    if (rows[read] == fullMask) {
      ++cleared;
    } else {
      rows[write--] = rows[read];
    }
  }
  for (uint8_t row = 0; row < cleared; ++row) rows[row] = 0;
  return cleared;
}

inline bool tetrisTSpinCorners(const uint16_t *rows, uint8_t width,
                               uint8_t height, int8_t pivotX,
                               int8_t pivotY) {
  if (rows == nullptr || width == 0 || height == 0) return false;
  uint8_t occupied = 0;
  static constexpr int8_t offsets[] = {-1, 1};
  for (const int8_t dy : offsets) {
    for (const int8_t dx : offsets) {
      const int8_t x = pivotX + dx;
      const int8_t y = pivotY + dy;
      occupied += x < 0 || x >= width || y < 0 || y >= height ||
                  (rows[y] & (1U << x));
    }
  }
  return occupied >= 3;
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

constexpr char classifyMorsePress(uint32_t heldMs, uint32_t dahThresholdMs) {
  return heldMs >= dahThresholdMs ? '-' : '.';
}

constexpr bool morseGapReached(uint32_t now, uint32_t elementEnd,
                               uint32_t gapMs) {
  return static_cast<int32_t>(now - elementEnd) >= static_cast<int32_t>(gapMs);
}

constexpr uint32_t macSuffix24(const uint8_t mac[6]) {
  return (static_cast<uint32_t>(mac[3]) << 16) |
         (static_cast<uint32_t>(mac[4]) << 8) | mac[5];
}

constexpr uint8_t MORSE_CHANNEL_MIN = 1;
constexpr uint8_t MORSE_CHANNEL_MAX = 13;

constexpr uint8_t stepMorseChannel(uint8_t channel, int8_t direction) {
  return direction < 0
             ? (channel <= MORSE_CHANNEL_MIN ? MORSE_CHANNEL_MAX : channel - 1)
             : (channel >= MORSE_CHANNEL_MAX ? MORSE_CHANNEL_MIN : channel + 1);
}

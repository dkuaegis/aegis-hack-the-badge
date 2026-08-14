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

// C0 is only ever driven LOW. The intended solution is C0-C2, with C1 open.
constexpr bool hiddenAccessMatched(bool challenge1Low, bool challenge2Low) {
  return !challenge1Low && challenge2Low;
}


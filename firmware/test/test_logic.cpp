#include <assert.h>

#include "logic.h"

int main() {
  uint8_t mask = 0;
  mask = markSolved(mask, 1);
  assert(!isSolved(mask, 0));
  assert(isSolved(mask, 1));
  assert(solvedMaskFor(5) == 0x1f);
  assert(legacyAuthResponse(0x1234, 0x1337) == 0x0103);
  assert(legacyAuthResponse(0xABCD, 0x1337) == 0xB8FA);
  assert(legacyAuthResponse(0x7777, 0x1337) == 0x6440);
  uint16_t hex = 0;
  assert(parseHex16("0000", hex) && hex == 0x0000);
  assert(parseHex16("4924", hex) && hex == 0x4924);
  assert(parseHex16("abcd", hex) && hex == 0xABCD);
  assert(parseHex16("ABCD", hex) && hex == 0xABCD);
  assert(!parseHex16("0x12", hex));
  assert(!parseHex16("123", hex));
  assert(!parseHex16("12345", hex));
  assert(!parseHex16("12G4", hex));
  assert(!parseHex16("", hex));
  assert(!hiddenAccessMatched(false, false));
  assert(!hiddenAccessMatched(true, true));
  assert(!hiddenAccessMatched(true, false));
  assert(hiddenAccessMatched(false, true));
  assert(!flappyCollision(28, 100, 32));
  assert(!flappyCollision(28, 30, 32));
  assert(flappyCollision(0, 100, 32));
  assert(flappyCollision(58, 100, 32));
  assert(flappyCollision(4, 30, 32));
  assert(rectsOverlap(10, 10, 3, 3, 12, 12, 5, 5));
  assert(!rectsOverlap(10, 10, 3, 3, 13, 10, 5, 5));
  assert(!rectsOverlap(10, 10, 3, 3, 10, 13, 5, 5));
  assert(stepLeaderboardChar('A', -1) == '9');
  assert(stepLeaderboardChar('Z', 1) == '0');
  assert(stepLeaderboardChar('9', 1) == 'A');
  assert(validLeaderboardName("A", 10));
  assert(validLeaderboardName("ZERO0COKE", 10));
  assert(!validLeaderboardName("", 10));
  assert(!validLeaderboardName("TOO-LONG-NAME", 10));
  assert(!validLeaderboardName("lower", 10));
  assert(decodeMorse(0b01, 2) == 'A');
  assert(decodeMorse(0b1000, 4) == 'B');
  assert(decodeMorse(0b000, 3) == 'S');
  assert(decodeMorse(0b111, 3) == 'O');
  assert(decodeMorse(0b1010, 4) == 'C');
  assert(decodeMorse(0b1101, 4) == 'Q');
  assert(decodeMorse(0b01111, 5) == '1');
  assert(decodeMorse(0b11111, 5) == '0');
  assert(decodeMorse(0b0011, 4) == '?');
  assert(classifyMorsePress(100, 200) == '.');
  assert(classifyMorsePress(199, 200) == '.');
  assert(classifyMorsePress(200, 200) == '-');
  assert(classifyMorsePress(300, 200) == '-');
  assert(!morseGapReached(400, 300, 300));  // C: dah -> dit, intra-gap
  assert(!morseGapReached(600, 500, 300));  // C: dit -> dah, intra-gap
  assert(!morseGapReached(800, 900, 300));  // active dah cannot end C early
  assert(morseGapReached(1400, 1100, 300)); // C -> Q, letter-gap
  constexpr uint8_t macA[] = {0xAA, 0xBB, 0xCC, 0x11, 0x22, 0x33};
  constexpr uint8_t macB[] = {0xAA, 0xBB, 0xCC, 0x44, 0x55, 0x66};
  static_assert(macSuffix24(macA) == 0x112233, "MAC suffix A");
  static_assert(macSuffix24(macB) == 0x445566, "MAC suffix B");
  static_assert(macSuffix24(macA) != macSuffix24(macB), "unique badge IDs");
  static_assert(stepMorseChannel(1, -1) == 13, "channel wraps left");
  static_assert(stepMorseChannel(13, 1) == 1, "channel wraps right");
  static_assert(stepMorseChannel(6, -1) == 5, "channel steps left");
  static_assert(stepMorseChannel(6, 1) == 7, "channel steps right");
}

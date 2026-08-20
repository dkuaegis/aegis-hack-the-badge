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
}

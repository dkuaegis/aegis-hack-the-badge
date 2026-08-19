#include <assert.h>

#include "logic.h"

int main() {
  uint8_t mask = 0;
  mask = markSolved(mask, 1);
  assert(!isSolved(mask, 0));
  assert(isSolved(mask, 1));
  assert(solvedMaskFor(5) == 0x1f);
  assert(!hiddenAccessMatched(false, false));
  assert(!hiddenAccessMatched(true, true));
  assert(!hiddenAccessMatched(true, false));
  assert(hiddenAccessMatched(false, true));
  assert(!flappyCollision(28, 100, 32));
  assert(!flappyCollision(28, 30, 32));
  assert(flappyCollision(0, 100, 32));
  assert(flappyCollision(58, 100, 32));
  assert(flappyCollision(4, 30, 32));
}

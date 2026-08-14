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
}


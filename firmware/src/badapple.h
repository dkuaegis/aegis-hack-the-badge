#pragma once

#include <stdint.h>

class U8G2;

const char *badAppleBegin(U8G2 &oled, void (*tone)(uint16_t));
void badAppleTick(uint32_t now, bool leftPressed, bool okPressed,
                  bool rightPressed, bool exitChord);
void badAppleEnd();
bool badAppleRunning();

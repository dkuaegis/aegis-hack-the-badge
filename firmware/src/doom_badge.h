#pragma once

#include <stdint.h>

#ifdef AEGIS_DOOM
class U8G2;
const char *doomBegin(U8G2 &oled, void (*tone)(uint16_t));
void doomTick();
void doomEnd();
bool doomRunning();
#endif

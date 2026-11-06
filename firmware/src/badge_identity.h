#pragma once

#include <stdint.h>
#include <stdio.h>

constexpr uint16_t BADGE_NUMBER_MAX = 999;
constexpr uint16_t BADGE_NUMBER_ADMIN = 0xffff;

inline void formatBadgeLabel(char *output, size_t size, uint16_t number,
                             uint32_t serial) {
  if (number == BADGE_NUMBER_ADMIN) snprintf(output, size, "ADMIN");
  else if (number > 0 && number <= BADGE_NUMBER_MAX)
    snprintf(output, size, "BADGE #%02u", static_cast<unsigned>(number));
  else snprintf(output, size, "AEGIS-%06lX", static_cast<unsigned long>(serial));
}

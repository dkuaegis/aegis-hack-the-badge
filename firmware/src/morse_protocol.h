#pragma once

#include <stdint.h>
#include "badge_identity.h"

constexpr uint16_t MORSE_PACKET_MAGIC = 0xae63;
constexpr uint8_t MORSE_PACKET_VERSION = 4;

struct __attribute__((packed)) MorsePacket {
  uint16_t magic;
  uint8_t version;
  char symbol;
  uint16_t durationMs;
  uint32_t sender;
  uint32_t receivedAt;
  uint16_t badgeNumber; // Display metadata only; sender is still derived from MAC.
};
static_assert(sizeof(MorsePacket) == 16, "Morse v4 wire format");

inline bool validMorsePacket(const MorsePacket &packet) {
  const bool element = packet.symbol == '.' || packet.symbol == '-';
  const bool boundary = packet.symbol == '/' || packet.symbol == ' ';
  return packet.magic == MORSE_PACKET_MAGIC &&
         packet.version == MORSE_PACKET_VERSION &&
         (packet.badgeNumber <= BADGE_NUMBER_MAX ||
          packet.badgeNumber == BADGE_NUMBER_ADMIN) &&
         ((element && packet.durationMs >= 30 && packet.durationMs <= 2000) ||
          (boundary && packet.durationMs == 0));
}

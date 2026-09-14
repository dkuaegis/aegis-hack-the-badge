#pragma once

#include <stdint.h>

constexpr uint16_t MORSE_PACKET_MAGIC = 0xae63;
constexpr uint8_t MORSE_PACKET_VERSION = 3;

struct __attribute__((packed)) MorsePacket {
  uint16_t magic;
  uint8_t version;
  char symbol;
  uint16_t durationMs;
  uint32_t sender;
  uint32_t receivedAt;
};
static_assert(sizeof(MorsePacket) == 14, "Morse v3 wire format");

inline bool validMorsePacket(const MorsePacket &packet) {
  const bool element = packet.symbol == '.' || packet.symbol == '-';
  const bool boundary = packet.symbol == '/' || packet.symbol == ' ';
  return packet.magic == MORSE_PACKET_MAGIC &&
         packet.version == MORSE_PACKET_VERSION &&
         ((element && packet.durationMs >= 30 && packet.durationMs <= 2000) ||
          (boundary && packet.durationMs == 0));
}

#pragma once

#include <stdint.h>

namespace Pins {
constexpr uint8_t OLED_SDA = 4;
constexpr uint8_t OLED_SCL = 5;

constexpr uint8_t CHALLENGE_0 = 6;
constexpr uint8_t CHALLENGE_1 = 7;
constexpr uint8_t CHALLENGE_2 = 8;

constexpr uint8_t BUTTON_LEFT = 9;
constexpr uint8_t BUTTON_OK = 10;
constexpr uint8_t BUTTON_RIGHT = 12;

constexpr uint8_t STATUS_LEDS[] = {13, 14, 15, 16, 17};
constexpr uint8_t BUZZER = 18;

constexpr uint8_t UART_TX = 43;
constexpr uint8_t UART_RX = 44;
} // namespace Pins


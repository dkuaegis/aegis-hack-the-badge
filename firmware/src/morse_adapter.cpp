#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

#include "logic.h"
#include "morse_protocol.h"

namespace {
QueueHandle_t received;
QueueHandle_t sent;
uint8_t channel = 1;
uint32_t ownId;
bool ready = false;
bool transmitting = false;
uint32_t sentAt = 0;
constexpr uint8_t broadcast[] = {255, 255, 255, 255, 255, 255};
char line[64];
size_t length = 0;
bool overflow = false;

constexpr uint8_t MORSE_LED_PIN = 38;
constexpr uint8_t MORSE_LED_BRIGHTNESS = 32; // 0-255; tune for the board/venue.
bool activityLit = false;
uint32_t activityUntil = 0;

void showActivityLed(bool sending, uint16_t durationMs) {
  if (durationMs == 0) return; // Letter/word boundaries are silent gaps.
  neopixelWrite(MORSE_LED_PIN, sending ? MORSE_LED_BRIGHTNESS : 0, 0,
                sending ? 0 : MORSE_LED_BRIGHTNESS);
  activityUntil = millis() + durationMs;
  activityLit = true; // The most recent TX/RX element determines the color.
}

void updateActivityLed() {
  if (activityLit && static_cast<int32_t>(millis() - activityUntil) >= 0) {
    neopixelWrite(MORSE_LED_PIN, 0, 0, 0);
    activityLit = false;
  }
}

void receivePacket(const uint8_t *mac, const uint8_t *data, int size) {
  if (!mac || size != sizeof(MorsePacket)) return;
  MorsePacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (!validMorsePacket(packet)) return;
  packet.sender = macSuffix24(mac);
  xQueueSend(received, &packet, 0);
}

void packetSent(const uint8_t *, esp_now_send_status_t status) {
  xQueueSend(sent, &status, 0);
}

void status() {
  if (!ready) Serial.println("ERR radio unavailable");
  else Serial.printf("READY 4 %u %06lX\n", channel, (unsigned long)ownId);
}

void command() {
  if (!ready) { status(); return; }
  if (transmitting) { Serial.println("ERR busy"); return; }
  if (!strcmp(line, "HELLO")) { status(); return; }
  unsigned next, symbol, duration;
  char extra;
  if (sscanf(line, "CHANNEL %u %c", &next, &extra) == 1 &&
      next >= MORSE_CHANNEL_MIN && next <= MORSE_CHANNEL_MAX) {
    if (esp_wifi_set_channel(next, WIFI_SECOND_CHAN_NONE) != ESP_OK) {
      Serial.println("ERR channel"); return;
    }
    channel = next;
    xQueueReset(received);
    status();
  } else if (sscanf(line, "TX %u %u %c", &symbol, &duration, &extra) == 2 &&
             symbol <= 127 && duration <= 2000) {
    const MorsePacket packet{MORSE_PACKET_MAGIC, MORSE_PACKET_VERSION,
                             static_cast<char>(symbol),
                             static_cast<uint16_t>(duration), ownId, 0,
                             BADGE_NUMBER_ADMIN};
    if (!validMorsePacket(packet)) { Serial.println("ERR packet"); return; }
    xQueueReset(sent);
    transmitting = true;
    sentAt = millis();
    if (esp_now_send(broadcast, reinterpret_cast<const uint8_t *>(&packet),
                     sizeof(packet)) != ESP_OK) {
      transmitting = false;
      Serial.println("ERR send");
    } else {
      showActivityLed(true, packet.durationMs);
    }
  } else Serial.println("ERR command");
}
} // namespace

void setup() {
  Serial.begin(115200);
  neopixelWrite(MORSE_LED_PIN, 0, 0, 0);
  received = xQueueCreate(32, sizeof(MorsePacket));
  sent = xQueueCreate(2, sizeof(esp_now_send_status_t));
  if (!received || !sent) return;
  WiFi.mode(WIFI_STA);
  uint8_t mac[6];
  WiFi.macAddress(mac);
  ownId = macSuffix24(mac);
  if (esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE) != ESP_OK ||
      esp_now_init() != ESP_OK) return;
  if (esp_now_register_recv_cb(receivePacket) != ESP_OK ||
      esp_now_register_send_cb(packetSent) != ESP_OK) return;
  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, broadcast, sizeof(broadcast));
  peer.ifidx = WIFI_IF_STA;
  ready = esp_now_add_peer(&peer) == ESP_OK;
}

void loop() {
  esp_now_send_status_t result;
  if (sent && xQueueReceive(sent, &result, 0) == pdTRUE && transmitting) {
    transmitting = false;
    Serial.println(result == ESP_NOW_SEND_SUCCESS ? "OK TX" : "ERR send");
  }
  if (transmitting && millis() - sentAt >= 2000) {
    transmitting = false;
    Serial.println("ERR send timeout");
    // Reset radio callbacks before accepting another send after a missing ACK.
    delay(20);
    ESP.restart();
  }
  MorsePacket packet;
  while (received && xQueueReceive(received, &packet, 0) == pdTRUE) {
    showActivityLed(false, packet.durationMs);
    Serial.printf("RX %06lX %u %u %u\n", (unsigned long)packet.sender,
                  (unsigned char)packet.symbol, packet.durationMs, packet.badgeNumber);
  }
  while (Serial.available()) {
    const char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      line[length] = '\0';
      if (overflow) Serial.println("ERR line too long");
      else command();
      length = 0;
      overflow = false;
    } else if (length + 1 < sizeof(line)) line[length++] = c;
    else overflow = true;
  }
  updateActivityLed();
  delay(1);
}

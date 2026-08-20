#include <Arduino.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <Preferences.h>
#include <U8g2lib.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <mbedtls/base64.h>
#include <mbedtls/md.h>
#include <stdarg.h>

#include "logic.h"
#include "logo.h"
#include "pins.h"
#include "problems.h"

namespace {
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint32_t BUTTON_DEBOUNCE_MS = 30;
constexpr uint32_t HIDDEN_HOLD_MS = 1200;
constexpr uint8_t FLAPPY_REWARD_SCORE = 5;
constexpr uint32_t FLAPPY_FRAME_MS = 40;
constexpr uint8_t HOME_MENU_COUNT = 4;
constexpr uint32_t FIREWALL_FRAME_MS = 30;
constexpr uint8_t FIREWALL_COLS = 8;
constexpr uint8_t FIREWALL_ROWS = 3;
constexpr int16_t FIREWALL_BRICK_X = 4;
constexpr int16_t FIREWALL_BRICK_Y = 10;
constexpr int16_t FIREWALL_BRICK_W = 13;
constexpr int16_t FIREWALL_BRICK_H = 5;
constexpr int16_t FIREWALL_BRICK_GAP_X = 2;
constexpr int16_t FIREWALL_BRICK_GAP_Y = 2;
constexpr int16_t FIREWALL_PADDLE_Y = 59;
constexpr int16_t FIREWALL_PADDLE_W = 24;
constexpr int16_t FIREWALL_PADDLE_H = 3;
constexpr int16_t FIREWALL_BALL_SIZE = 3;
constexpr float FIREWALL_PADDLE_SPEED = 85.0f;
constexpr uint32_t TROPHY_LED_STEP_MS = 120;
constexpr uint32_t LONG_PRESS_MS = 700;
constexpr char START_COMMAND[] = "aegis";
constexpr char BLE_SERVICE_UUID[] = "6f8d0001-6a4b-4c52-9f2a-8f0f5d9b0001";
constexpr char BLE_RX_UUID[] = "6f8d0002-6a4b-4c52-9f2a-8f0f5d9b0001";
constexpr char BLE_TX_UUID[] = "6f8d0003-6a4b-4c52-9f2a-8f0f5d9b0001";
#ifndef BADGE_ADMIN_KEY
#define BADGE_ADMIN_KEY "AEGIS_DEV_ONLY_CHANGE_ME"
#endif
// ponytail: 행사 전 fleet key를 교체하세요. 장비 탈취 위협이 생기면 NVS 장비별 키로 전환합니다.
constexpr char BLE_ADMIN_KEY[] = BADGE_ADMIN_KEY;
constexpr size_t BLE_COMMAND_MAX = 768;
constexpr size_t BLE_NOTIFY_CHUNK = 20;

Preferences preferences;
U8G2_SSD1315_128X64_NONAME_1_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE,
                                         Pins::OLED_SCL, Pins::OLED_SDA);

uint8_t solvedMask = 0;
Problem problems[SERIAL_PROBLEM_COUNT] = {};
int8_t displayedProblem = -1;
uint8_t menuItem = 0;
uint8_t browserProblem = 0;
uint32_t hiddenSince = 0;
uint32_t hiddenVictoryAt = 0;
char serialLine[192] = {};
uint8_t serialLength = 0;
char badgeId[19] = {};
BLEServer *bleServer = nullptr;
BLECharacteristic *bleTx = nullptr;
QueueHandle_t bleCommands = nullptr;
volatile bool bleConnected = false;
volatile bool bleRestartAdvertising = false;
volatile bool bleAuthenticated = false;
bool bleStatusDirty = false;
uint32_t bleChallenge = 0;
uint32_t rebootAt = 0;
char bleRxLine[BLE_COMMAND_MAX] = {};
size_t bleRxLength = 0;

struct BleCommand {
  char text[BLE_COMMAND_MAX];
};

void bleSendLine(const char *line);

enum class PlayerTarget : uint8_t { Usb, Ble };

struct PlayerContext {
  int8_t problem = -1;
  bool diagnostic = false;
  bool challengeValid = false;
  uint16_t challenge = 0;
};

PlayerContext usbPlayer;
PlayerContext blePlayer;
uint16_t displayedAuthChallenge = 0;

PlayerContext &playerContext(PlayerTarget target) {
  return target == PlayerTarget::Usb ? usbPlayer : blePlayer;
}

void resetPlayer(PlayerContext &player) {
  player.problem = -1;
  player.diagnostic = false;
  player.challengeValid = false;
  player.challenge = 0;
}

void playerLine(PlayerTarget target, const char *line) {
  if (target == PlayerTarget::Usb) Serial.println(line);
  else bleSendLine(line);
}

void playerPrintf(PlayerTarget target, const char *format, ...) {
  char line[320];
  va_list args;
  va_start(args, format);
  vsnprintf(line, sizeof(line), format, args);
  va_end(args);
  playerLine(target, line);
}

enum class Screen : uint8_t {
  Home, Problems, Hint, Status, Game, FirewallGame, HiddenGranted, Complete
};
enum class GamePhase : uint8_t { Intro, Running, Over };
enum class FirewallPhase : uint8_t { Intro, Running, Over, Clear };
enum class VictoryPhase : uint8_t {
  Idle, FlashOn1, FlashOff1, FlashOn2, Fanfare, TrophyIdle
};
Screen screen = Screen::Home;
GamePhase gamePhase = GamePhase::Intro;

struct FlappyState {
  float birdY = 28;
  float velocity = 0;
  float pipeX = 128;
  int8_t gapY = 32;
  uint8_t score = 0;
  bool passed = false;
  uint32_t lastFrame = 0;
} game;

struct FirewallState {
  FirewallPhase phase = FirewallPhase::Intro;
  float ballX = 64;
  float ballY = 46;
  float ballVX = 42;
  float ballVY = -46;
  float paddleX = 52;
  bool bricks[FIREWALL_ROWS][FIREWALL_COLS] = {};
  uint8_t remaining = 0;
  uint32_t lastFrame = 0;
} firewall;

struct VictoryNote {
  uint16_t frequency;
  uint16_t duration;
  uint16_t gap;
};

constexpr VictoryNote VICTORY_MELODY[] = {
    {523, 90, 25},  {659, 90, 25},  {784, 90, 25},
    {1047, 180, 40}, {784, 90, 25}, {1047, 90, 25},
    {1319, 140, 30}, {1568, 360, 0},
};

struct VictoryState {
  VictoryPhase phase = VictoryPhase::Idle;
  bool active = false;
  bool ledSweep = false;
  bool notePlaying = false;
  uint8_t melodyIndex = 0;
  uint32_t nextAt = 0;
  int8_t ledPosition = 0;
  int8_t ledDirection = 1;
  uint32_t ledNextAt = 0;
} victory;

struct Button {
  uint8_t pin;
  bool stable = false;
  bool raw = false;
  bool pressed = false;
  bool longPressed = false;
  bool longFired = false;
  uint32_t changedAt = 0;
  uint32_t heldAt = 0;

  explicit Button(uint8_t buttonPin) : pin(buttonPin) {}

  void begin() {
    pinMode(pin, INPUT_PULLUP);
    stable = raw = digitalRead(pin) == LOW;
  }

  void update(uint32_t now) {
    pressed = false;
    longPressed = false;
    const bool next = digitalRead(pin) == LOW;
    if (next != raw) {
      raw = next;
      changedAt = now;
    }
    if (raw != stable && now - changedAt >= BUTTON_DEBOUNCE_MS) {
      stable = raw;
      pressed = stable;
      if (stable) {
        heldAt = now;
        longFired = false;
      }
    }
    if (stable && !longFired && now - heldAt >= LONG_PRESS_MS) {
      longPressed = true;
      longFired = true;
    }
  }
};

Button left{Pins::BUTTON_LEFT};
Button ok{Pins::BUTTON_OK};
Button right{Pins::BUTTON_RIGHT};

void centered(uint8_t baseline, const char *text) {
  const uint8_t width = oled.getStrWidth(text);
  oled.drawStr(width < 128 ? (128 - width) / 2 : 0, baseline, text);
}

void header(const char *text) {
  oled.setFont(u8g2_font_5x7_tf);
  centered(7, text);
  oled.drawHLine(38, 10, 52);
}

void footer(const char *text) {
  oled.setFont(u8g2_font_5x7_tf);
  centered(63, text);
}

void inverseLabel(uint8_t y, uint8_t height, const char *text) {
  oled.setFont(u8g2_font_5x7_tf);
  const uint8_t width = min<uint8_t>(oled.getStrWidth(text) + 12, 112);
  const uint8_t x = (128 - width) / 2;
  oled.drawBox(x, y, width, height);
  oled.setDrawColor(0);
  centered(y + height - 2, text);
  oled.setDrawColor(1);
}

void render(void (*frame)()) {
  oled.firstPage();
  do frame(); while (oled.nextPage());
}

uint8_t solvedCount() {
  uint8_t count = 0;
  for (uint8_t i = 0; i < TOTAL_CHALLENGE_COUNT; ++i) {
    count += isSolved(solvedMask, i);
  }
  return count;
}

uint8_t serialSolvedCount() {
  uint8_t count = 0;
  for (uint8_t i = 0; i < SERIAL_PROBLEM_COUNT; ++i) {
    count += isSolved(solvedMask, i);
  }
  return count;
}

bool allSolved() {
  return (solvedMask & solvedMaskFor(TOTAL_CHALLENGE_COUNT)) ==
         solvedMaskFor(TOTAL_CHALLENGE_COUNT);
}

void updateProgressLeds() {
  for (uint8_t i = 0; i < TOTAL_CHALLENGE_COUNT; ++i) {
    digitalWrite(Pins::STATUS_LEDS[i], isSolved(solvedMask, i) ? HIGH : LOW);
  }
}

void setAllStatusLeds(bool on) {
  for (uint8_t pin : Pins::STATUS_LEDS) digitalWrite(pin, on ? HIGH : LOW);
}

void stopVictoryMode() {
  noTone(Pins::BUZZER);
  victory = VictoryState{};
  hiddenVictoryAt = 0;
}

void saveMask() {
  preferences.putUChar("solved", solvedMask);
  updateProgressLeds();
  bleStatusDirty = true;
}

void problemKey(uint8_t index, char key[4]) {
  snprintf(key, 4, "p%u", index + 1);
}

bool asciiText(const char *text) {
  for (; *text; ++text) {
    if (static_cast<uint8_t>(*text) > 0x7f) return false;
  }
  return true;
}

bool validProblem(const Problem &problem) {
  if (problem.version != PROBLEM_STORAGE_VERSION ||
      (problem.type != 'F' && problem.type != 'C') ||
      problem.optionCount > PROBLEM_OPTION_MAX || problem.title[0] == '\0' ||
      problem.answer[0] == '\0' || problem.serialText[0] == '\0' ||
      problem.title[PROBLEM_TITLE_SIZE - 1] != '\0' ||
      problem.answer[PROBLEM_ANSWER_SIZE - 1] != '\0' ||
      problem.serialText[PROBLEM_TEXT_SIZE - 1] != '\0' ||
      !asciiText(problem.title)) return false;
  for (uint8_t i = 0; i < PROBLEM_OPTION_MAX; ++i) {
    if (problem.oledLines[i][PROBLEM_OPTION_SIZE - 1] != '\0' ||
        !asciiText(problem.oledLines[i])) return false;
  }
  if (problem.type == 'C') {
    if (problem.optionCount < 2 || strlen(problem.answer) != 1 ||
        problem.answer[0] < '1' ||
        problem.answer[0] >= '1' + problem.optionCount) return false;
    for (uint8_t i = 0; i < problem.optionCount; ++i) {
      if (problem.oledLines[i][0] == '\0') return false;
    }
  }
  return true;
}

void loadProblems() {
  for (uint8_t i = 0; i < SERIAL_PROBLEM_COUNT; ++i) {
    char key[4];
    problemKey(i, key);
    if (preferences.getBytesLength(key) == sizeof(Problem)) {
      preferences.getBytes(key, &problems[i], sizeof(Problem));
    }
    if (!validProblem(problems[i])) problems[i] = DEFAULT_PROBLEMS[i];
  }
}

void saveProblem(uint8_t index) {
  char key[4];
  problemKey(index, key);
  preferences.putBytes(key, &problems[index], sizeof(Problem));
}

void configureHiddenAccessPins() {
  hiddenSince = 0;
  if (isSolved(solvedMask, HIDDEN_ACCESS_INDEX)) {
    pinMode(Pins::CHALLENGE_0, INPUT);
    pinMode(Pins::CHALLENGE_1, INPUT);
    pinMode(Pins::CHALLENGE_2, INPUT);
    return;
  }
  pinMode(Pins::CHALLENGE_0, OUTPUT);
  digitalWrite(Pins::CHALLENGE_0, LOW);
  pinMode(Pins::CHALLENGE_1, INPUT_PULLUP);
  pinMode(Pins::CHALLENGE_2, INPUT_PULLUP);
}

void beep(uint16_t frequency = 880, uint16_t duration = 70) {
  tone(Pins::BUZZER, frequency, duration);
}

void drawBootFrame() {
  oled.drawXBMP(32, 0, 64, 64, AEGIS_LOGO_64);
}

void drawBoot() { render(drawBootFrame); }

void drawHomeFrame() {
  static const char *const items[HOME_MENU_COUNT] = {
      "MISSIONS", "FLAPPY HACKER", "FIREWALL BREAKER", "STATUS"};
  char progress[8];
  snprintf(progress, sizeof(progress), "%02u / %02u", serialSolvedCount(),
           static_cast<unsigned>(SERIAL_PROBLEM_COUNT));
  header("AEGIS // MSGCTF");
  oled.setFont(u8g2_font_9x15B_tf);
  centered(27, progress);
  oled.drawFrame(42, 31, 44, 6);
  const uint8_t fill = serialSolvedCount() * 40 / SERIAL_PROBLEM_COUNT;
  if (fill) oled.drawBox(44, 33, fill, 2);
  inverseLabel(41, 11, items[menuItem]);
  footer("<     SELECT     >");
}

void drawHome() { render(drawHomeFrame); }

void drawProblemsFrame() {
  char title[24];
  snprintf(title, sizeof(title), "MISSION %02u / %02u", browserProblem + 1,
           static_cast<unsigned>(SERIAL_PROBLEM_COUNT));
  char number[4];
  snprintf(number, sizeof(number), "%02u", browserProblem + 1);
  header(title);
  oled.setFont(u8g2_font_9x15B_tf);
  centered(27, number);
  oled.setFont(u8g2_font_6x10_tf);
  centered(38, problems[browserProblem].title);
  inverseLabel(41, 10,
               isSolved(solvedMask, browserProblem) ? "MISSION CLEARED" : "NEW MISSION");
  footer("<      OPEN      >");
}

void drawProblems() { render(drawProblemsFrame); }

void drawHintFrame() {
  char title[24];
  snprintf(title, sizeof(title), "%02u // %s", displayedProblem + 1,
           problems[displayedProblem].title);
  header(title);
  oled.setFont(u8g2_font_5x7_tf);
  for (uint8_t row = 0; row < PROBLEM_OPTION_MAX; ++row) {
    centered(19 + row * 9, problems[displayedProblem].oledLines[row]);
  }
  footer(problems[displayedProblem].type == 'C'
             ? "CHOICE VIA SHELL"
             : "FLAG VIA SHELL");
}

void drawHint(uint8_t index) {
  displayedProblem = index;
  render(drawHintFrame);
}

void drawDiagnosticAccessFrame() {
  header("03 // MAINTENANCE");
  oled.setFont(u8g2_font_6x10_tf);
  centered(21, "DIAGNOSTIC");
  centered(31, "INTERFACE");
  inverseLabel(37, 12, "ACCESS GRANTED");
  footer("FLAG VIA SHELL");
}

void drawDiagnosticAccess() {
  screen = Screen::Hint;
  displayedProblem = MISSION_MAINTENANCE;
  render(drawDiagnosticAccessFrame);
}

void drawLegacyAuthChallengeFrame() {
  char challenge[12];
  snprintf(challenge, sizeof(challenge), "%04X", displayedAuthChallenge);
  header("AUTH REQUIRED");
  oled.setFont(u8g2_font_6x10_tf);
  centered(25, "CHALLENGE");
  oled.setFont(u8g2_font_9x15B_tf);
  centered(43, challenge);
  footer("AUTH XXXX VIA SHELL");
}

void drawLegacyAuthChallenge(uint16_t challenge) {
  screen = Screen::Hint;
  displayedProblem = MISSION_LEGACY_AUTH;
  displayedAuthChallenge = challenge;
  render(drawLegacyAuthChallengeFrame);
}

void drawLegacyAuthSuccessFrame() {
  header("AUTH SUCCESS");
  oled.setFont(u8g2_font_6x10_tf);
  centered(27, "ACCESS");
  inverseLabel(32, 14, "ELEVATED");
  footer("MISSION CLEAR");
}

void drawLegacyAuthSuccess() {
  screen = Screen::Hint;
  displayedProblem = MISSION_LEGACY_AUTH;
  render(drawLegacyAuthSuccessFrame);
}

void drawStatusFrame() {
  char total[8];
  const bool hiddenSolved = isSolved(solvedMask, HIDDEN_ACCESS_INDEX);
  snprintf(total, sizeof(total), "%u / %u",
           hiddenSolved ? solvedCount() : serialSolvedCount(),
           static_cast<unsigned>(hiddenSolved ? TOTAL_CHALLENGE_COUNT
                                              : SERIAL_PROBLEM_COUNT));
  header("BADGE STATUS");
  oled.setFont(u8g2_font_9x15B_tf);
  centered(hiddenSolved ? 25 : 29, total);
  oled.setFont(u8g2_font_6x10_tf);
  if (hiddenSolved) {
    char serial[16];
    snprintf(serial, sizeof(serial), "SERIAL %u / %u", serialSolvedCount(),
             static_cast<unsigned>(SERIAL_PROBLEM_COUNT));
    centered(38, serial);
    oled.setFont(u8g2_font_5x7_tf);
    inverseLabel(43, 10, "HIDDEN ACCESS CLEAR");
  } else {
    centered(45, "SERIAL MISSIONS");
  }
  footer("HOLD OK: BACK");
}

void drawStatus() { render(drawStatusFrame); }

void drawHiddenGrantedFrame() {
  oled.setFont(u8g2_font_6x10_tf);
  centered(14, "HIDDEN ACCESS");
  oled.setFont(u8g2_font_9x18B_tf);
  oled.drawBox(24, 18, 80, 22);
  oled.setDrawColor(0);
  centered(36, "GRANTED");
  oled.setDrawColor(1);
  oled.setFont(u8g2_font_6x10_tf);
  centered(50, "CHALLENGE 05 CLEAR");
  footer("OK: STATUS");
}

void drawHiddenGranted() { render(drawHiddenGrantedFrame); }

void resetProgress() {
  stopVictoryMode();
  solvedMask = 0;
  saveMask();
  configureHiddenAccessPins();
  resetPlayer(usbPlayer);
  resetPlayer(blePlayer);
  displayedProblem = -1;
  screen = Screen::Status;
  drawStatus();
}

void drawCompleteFrame() {
  constexpr char trophy[] = "AEGIS{PWN3D!}";
  oled.setFont(u8g2_font_5x7_tf);
  centered(8, "Congratulations!");
  oled.setFont(u8g2_font_9x15B_tf);
  if (oled.getStrWidth(trophy) > 126) oled.setFont(u8g2_font_8x13B_tf);
  centered(39, trophy);
  oled.setFont(u8g2_font_4x6_tf);
  centered(59, "You solved all problems XD");
}

void drawComplete() { render(drawCompleteFrame); }

void printVictoryMessage() {
  Serial.println(F("\n================================"));
  Serial.println(F("   모든 문제를 해결했습니다!"));
  Serial.println(F("================================\n"));
  Serial.println(F("축하합니다!"));
  Serial.println(F("AEGIS Hack The Badge의 모든 Challenge를 완료했습니다."));
  Serial.println(F("\nAEGIS{PWN3D!}"));
}

void startVictorySequence(uint32_t now) {
  resetPlayer(usbPlayer);
  resetPlayer(blePlayer);
  screen = Screen::Complete;
  drawComplete();
  printVictoryMessage();
  victory = VictoryState{};
  victory.active = true;
  victory.phase = VictoryPhase::FlashOn1;
  victory.nextAt = now + 250;
  setAllStatusLeds(true);
  bleStatusDirty = true;
}

void enterTrophyModeFromBoot(uint32_t now) {
  stopVictoryMode();
  screen = Screen::Complete;
  drawComplete();
  victory.phase = VictoryPhase::TrophyIdle;
  victory.ledSweep = true;
  victory.ledPosition = 0;
  victory.ledDirection = 1;
  victory.ledNextAt = now;
  setAllStatusLeds(false);
}

void updateVictory(uint32_t now) {
  if (!victory.active || static_cast<int32_t>(now - victory.nextAt) < 0) return;

  if (victory.phase == VictoryPhase::FlashOn1) {
    setAllStatusLeds(false);
    victory.phase = VictoryPhase::FlashOff1;
    victory.nextAt = now + 120;
  } else if (victory.phase == VictoryPhase::FlashOff1) {
    setAllStatusLeds(true);
    victory.phase = VictoryPhase::FlashOn2;
    victory.nextAt = now + 250;
  } else if (victory.phase == VictoryPhase::FlashOn2) {
    victory.phase = VictoryPhase::Fanfare;
    victory.nextAt = now;
  } else if (victory.phase == VictoryPhase::Fanfare) {
    if (victory.notePlaying) {
      noTone(Pins::BUZZER);
      victory.notePlaying = false;
      victory.nextAt = now + VICTORY_MELODY[victory.melodyIndex].gap;
      ++victory.melodyIndex;
    } else if (victory.melodyIndex <
               sizeof(VICTORY_MELODY) / sizeof(VICTORY_MELODY[0])) {
      const VictoryNote &note = VICTORY_MELODY[victory.melodyIndex];
      tone(Pins::BUZZER, note.frequency, note.duration);
      victory.notePlaying = true;
      victory.nextAt = now + note.duration;
    } else {
      victory.active = false;
      victory.ledSweep = true;
      victory.phase = VictoryPhase::TrophyIdle;
      victory.ledPosition = 0;
      victory.ledDirection = 1;
      victory.ledNextAt = now;
    }
  }
}

void updateTrophyLedSweep(uint32_t now) {
  if (!victory.ledSweep || static_cast<int32_t>(now - victory.ledNextAt) < 0) return;
  setAllStatusLeds(false);
  digitalWrite(Pins::STATUS_LEDS[victory.ledPosition], HIGH);
  if (victory.ledPosition == TOTAL_CHALLENGE_COUNT - 1) victory.ledDirection = -1;
  else if (victory.ledPosition == 0) victory.ledDirection = 1;
  victory.ledPosition += victory.ledDirection;
  victory.ledNextAt = now + TROPHY_LED_STEP_MS;
}

void solveAllForAdmin(uint32_t now) {
  if (allSolved()) return;
  solvedMask = solvedMaskFor(TOTAL_CHALLENGE_COUNT);
  saveMask();
  configureHiddenAccessPins();
  startVictorySequence(now);
}

void printBanner() {
  Serial.println();
  Serial.println(F("=== Aegis Hack The Badge / Rev.3 ==="));
  Serial.println(F("문제 본문: Serial / 보기와 예시: OLED"));
  Serial.println(F("명령: 1-4, status, help, hint, exit, clear, aegis"));
}

void printStatus() {
  Serial.println(F("\n[challenge status]"));
  for (uint8_t i = 0; i < SERIAL_PROBLEM_COUNT; ++i) {
    Serial.printf("%u. %-13s [%c]\n", i + 1, problems[i].title,
                  isSolved(solvedMask, i) ? 'O' : 'X');
  }
}

uint16_t legacyAuthKey() {
  return static_cast<uint16_t>((ESP.getEfuseMac() & 0xffffU) ^ 0x1337U);
}

void printLeakedTransmission(PlayerTarget target) {
  char hex[PROBLEM_ANSWER_SIZE * 3] = {};
  size_t used = 0;
  const char *answer = problems[MISSION_LEAKED].answer;
  for (size_t i = 0; answer[i] != '\0' && used + 4 < sizeof(hex); ++i) {
    const int written = snprintf(hex + used, sizeof(hex) - used, "%s%02X",
                                 i == 0 ? "" : " ",
                                 static_cast<uint8_t>(answer[i]));
    if (written < 0) break;
    used += static_cast<size_t>(written);
  }
  playerLine(target, "\n[CAPTURED PAYLOAD // HEX]");
  playerLine(target, hex);
}

void startProblem(PlayerTarget target, uint8_t index) {
  PlayerContext &player = playerContext(target);
  resetPlayer(player);
  player.problem = index;
  screen = Screen::Hint;
  drawHint(index);
  playerLine(target, "");
  playerLine(target, problems[index].serialText);
  if (index == MISSION_LEAKED) {
    printLeakedTransmission(target);
    playerLine(target, "\n복원한 FLAG를 입력하세요. 종료: exit");
  } else if (index == MISSION_DEBUG) {
    playerLine(target, "\n디버그 콘솔이 열렸습니다. 명령을 조사하세요.");
  } else if (index == MISSION_MAINTENANCE) {
    playerLine(target, "\n유지보수 콘솔이 열렸습니다. 숨겨진 기능을 찾으세요.");
  } else {
    playerLine(target, "\n레거시 인증 콘솔이 열렸습니다. 진단 인터페이스를 찾으세요.");
  }
  beep(659);
}

void showProblem(uint8_t index) { startProblem(PlayerTarget::Usb, index); }

void finishProblem(PlayerTarget target, uint8_t index) {
  const bool completedBefore = allSolved();
  const uint8_t next = markSolved(solvedMask, index);
  if (next != solvedMask) {
    solvedMask = next;
    saveMask();
  }
  playerPrintf(target, "정답입니다. 진행도: %u/%u", serialSolvedCount(),
               static_cast<unsigned>(SERIAL_PROBLEM_COUNT));
  resetPlayer(playerContext(target));
  if (!completedBefore && allSolved()) {
    startVictorySequence(millis());
  } else if (allSolved()) {
    screen = Screen::Complete;
    drawComplete();
  } else {
    beep(1047, 130);
    screen = Screen::Status;
    drawStatus();
  }
}

void incorrect(PlayerTarget target) {
  playerLine(target, "정답이 아닙니다. 다시 시도하거나 exit를 입력하세요.");
  beep(196, 150);
}

void printLegacyLog(PlayerTarget target) {
  constexpr uint16_t history[] = {0x1234, 0xABCD, 0x7777};
  const uint16_t key = legacyAuthKey();
  playerLine(target, "[AUTH HISTORY]");
  for (uint16_t challenge : history) {
    playerPrintf(target, "challenge=%04X response=%04X", challenge,
                 legacyAuthResponse(challenge, key));
  }
}

void handleLegacyAuth(PlayerTarget target, char *input) {
  PlayerContext &player = playerContext(target);
  if (!player.diagnostic) {
    if (strcmp(input, "diag") == 0) {
      player.diagnostic = true;
      playerLine(target, "진단 셸에 접속했습니다. help를 입력하세요.");
    } else if (strcmp(input, "help") == 0) {
      playerLine(target, "사용 가능: help, diag, hint, exit");
    } else {
      playerLine(target, "인증 절차를 통해야 보상 FLAG를 획득할 수 있습니다.");
    }
    return;
  }

  if (strcmp(input, "exit") == 0) {
    player.diagnostic = false;
    player.challengeValid = false;
    player.challenge = 0;
    drawHint(MISSION_LEGACY_AUTH);
    playerLine(target, "진단 셸에서 나왔습니다. 문제 종료: exit");
  } else if (strcmp(input, "help") == 0) {
    playerLine(target, "사용 가능: help, dump, log, auth, auth XXXX, exit");
  } else if (strcmp(input, "dump") == 0) {
    playerLine(target, "[AUTH CONFIGURATION]");
    playerLine(target, "인증 방식 : legacy-v1");
    playerPrintf(target, "Device ID : %.12s", badgeId);
  } else if (strcmp(input, "log") == 0) {
    printLegacyLog(target);
  } else if (strcmp(input, "auth") == 0) {
    do player.challenge = static_cast<uint16_t>(esp_random());
    while (player.challenge == 0);
    player.challengeValid = true;
    playerPrintf(target, "challenge: %04X", player.challenge);
    playerLine(target, "응답 형식: auth XXXX (16진수 4자리)");
    drawLegacyAuthChallenge(player.challenge);
  } else if (strncmp(input, "auth ", 5) == 0) {
    uint16_t response = 0;
    if (!player.challengeValid) {
      playerLine(target, "먼저 auth로 challenge를 발급받으세요.");
    } else if (!parseHex16(input + 5, response)) {
      playerLine(target, "응답은 16진수 4자리여야 합니다. 예: auth 1A2B");
    } else if (response != legacyAuthResponse(player.challenge, legacyAuthKey())) {
      playerLine(target, "AUTH FAILED. 같은 challenge로 다시 시도하세요.");
      beep(196, 150);
    } else {
      player.challengeValid = false;
      playerLine(target, "AUTH SUCCESS");
      playerPrintf(target, "[REWARD FLAG] %s", problems[MISSION_LEGACY_AUTH].answer);
      drawLegacyAuthSuccess();
      finishProblem(target, MISSION_LEGACY_AUTH);
    }
  } else {
    playerLine(target, "알 수 없는 진단 명령입니다. help를 입력하세요.");
  }
}

void handleProblemInput(PlayerTarget target, char *input) {
  PlayerContext &player = playerContext(target);
  const uint8_t index = static_cast<uint8_t>(player.problem);

  if (strcmp(input, "hint") == 0) {
    drawHint(index);
    playerLine(target, "OLED에 보기/예시를 다시 표시했습니다.");
    return;
  }
  if (index == MISSION_LEGACY_AUTH && player.diagnostic) {
    handleLegacyAuth(target, input);
    return;
  }
  if (strcmp(input, "exit") == 0) {
    resetPlayer(player);
    screen = Screen::Home;
    drawHome();
    playerLine(target, "문제에서 나왔습니다.");
    return;
  }

  if (index == MISSION_LEAKED) {
    if (strcmp(input, problems[index].answer) == 0) finishProblem(target, index);
    else incorrect(target);
  } else if (index == MISSION_DEBUG) {
    if (strcmp(input, problems[index].answer) == 0) {
      finishProblem(target, index);
    } else if (strcmp(input, "help") == 0) {
      playerLine(target, "사용 가능: help, info, log, hint, exit");
    } else if (strcmp(input, "info") == 0) {
      playerLine(target, "[DEVICE INFORMATION]");
      playerLine(target, "장치명      : AEGIS BADGE Rev.3");
      playerLine(target, "펌웨어      : 3.x");
      playerLine(target, "동작 모드   : PLAYER");
      playerLine(target, "디버그 모드 : ENABLED");
      playerLine(target, "경고: 운영 환경에서 디버그 기능이 활성화되어 있습니다.");
    } else if (strcmp(input, "log") == 0) {
      playerLine(target, "[SYSTEM LOG]");
      playerLine(target, "10:31:02 시스템 부팅 완료");
      playerLine(target, "10:31:02 OLED 초기화 완료");
      playerLine(target, "10:31:03 Serial Console 시작");
      playerLine(target, "10:31:03 사용자 문제 데이터 로드");
      playerPrintf(target, "10:31:03 DEBUG: recovery_token=%s",
                   problems[index].answer);
    } else {
      playerLine(target, "알 수 없는 디버그 명령입니다. help를 입력하세요.");
    }
  } else if (index == MISSION_MAINTENANCE) {
    if (strcmp(input, problems[index].answer) == 0) {
      finishProblem(target, index);
    } else if (strcmp(input, "help") == 0) {
      playerLine(target, "사용 가능: help, info, hint, exit");
    } else if (strcmp(input, "info") == 0) {
      playerLine(target, "[DEVICE INFORMATION]");
      playerLine(target, "장치명 : AEGIS BADGE Rev.3");
      playerLine(target, "빌드   : rev3-prod");
      playerLine(target, "로드된 모듈: display, storage, serial, diag");
    } else if (strcmp(input, "diag") == 0) {
      playerLine(target, "[DIAGNOSTIC INTERFACE]");
      playerLine(target, "유지보수 인터페이스에 접근했습니다.");
      playerLine(target, "운영 펌웨어에서 관리자용 진단 기능이 노출되어 있습니다.");
      playerPrintf(target, "FLAG: %s", problems[index].answer);
      playerLine(target, "FLAG를 제출하거나 exit를 입력하세요.");
      drawDiagnosticAccess();
    } else {
      playerLine(target, "알 수 없는 유지보수 명령입니다. help를 입력하세요.");
    }
  } else {
    handleLegacyAuth(target, input);
  }
}

void handleSerialLine(char *input) {
  while (*input == ' ' || *input == '\t') ++input;
  char *end = input + strlen(input);
  while (end > input && (end[-1] == ' ' || end[-1] == '\t')) --end;
  *end = '\0';
  if (*input == '\0') return;

  if (usbPlayer.problem >= 0) {
    handleProblemInput(PlayerTarget::Usb, input);
    return;
  }

  if (strlen(input) == 1 && input[0] >= '1' &&
      input[0] < '1' + static_cast<int>(SERIAL_PROBLEM_COUNT)) {
    showProblem(input[0] - '1');
  } else if (strcmp(input, "status") == 0) {
    printStatus();
  } else if (strcmp(input, "help") == 0) {
    Serial.println(F("사용 가능한 명령어:"));
    Serial.println(F("  1-4       문제 선택"));
    Serial.println(F("  status    문제 진행 상태 확인"));
    Serial.println(F("  help      도움말"));
    Serial.println(F("  clear     콘솔 화면 정리"));
    Serial.println(F("  aegis     배지 정보 다시 표시"));
    Serial.println(F("문제 내부에서는 각 문제에 맞는 명령을 사용할 수 있습니다."));
  } else if (strcmp(input, "hint") == 0) {
    Serial.println(F("먼저 1-4 중 문제를 선택하세요."));
  } else if (strcmp(input, "clear") == 0) {
    for (uint8_t i = 0; i < 30; ++i) Serial.println();
  } else if (strcmp(input, START_COMMAND) == 0) {
    printBanner();
  } else {
    Serial.println(F("알 수 없는 명령입니다. help를 입력하세요."));
  }
}

void pollSerial() {
  while (Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      serialLine[serialLength] = '\0';
      handleSerialLine(serialLine);
      serialLength = 0;
    } else if (serialLength + 1 < sizeof(serialLine)) {
      serialLine[serialLength++] = c;
    } else {
      serialLength = 0;
      Serial.println(F("입력이 너무 깁니다."));
    }
  }
}

void drawBird(float x, float y) {
  oled.drawBox(static_cast<uint8_t>(x), static_cast<uint8_t>(y + 1), 7, 5);
  oled.drawBox(static_cast<uint8_t>(x + 2), static_cast<uint8_t>(y), 4, 1);
  if (x >= 2) oled.drawBox(static_cast<uint8_t>(x - 2), static_cast<uint8_t>(y + 3), 3, 2);
  oled.setDrawColor(0);
  oled.drawPixel(static_cast<uint8_t>(x + 5), static_cast<uint8_t>(y + 2));
  oled.setDrawColor(1);
}

void drawGameIntroFrame() {
  header("FLAPPY HACKER");
  drawBird(61, 21);
  oled.setFont(u8g2_font_6x10_tf);
  centered(43, "PRESS OK");
  oled.setFont(u8g2_font_5x7_tf);
  centered(52, "SCORE 5 = HINT");
  footer("LEFT: EXIT");
}

void drawGameIntro() { render(drawGameIntroFrame); }

void drawGameRunningFrame() {
  char score[4];
  snprintf(score, sizeof(score), "%u", game.score);
  oled.setFont(u8g2_font_5x7_tf);
  centered(7, score);
  drawBird(28, game.birdY);

  const int16_t x = static_cast<int16_t>(game.pipeX);
  const int16_t gapTop = game.gapY - 13;
  const int16_t gapBottom = game.gapY + 13;
  if (x < 128 && x + 11 > 0) {
    oled.drawBox(max<int16_t>(x, 0), 0, min<int16_t>(11, 128 - max<int16_t>(x, 0)), gapTop);
    oled.drawBox(max<int16_t>(x, 0), gapBottom,
                 min<int16_t>(11, 128 - max<int16_t>(x, 0)), 64 - gapBottom);
    oled.drawBox(max<int16_t>(x - 2, 0), gapTop - 3,
                 min<int16_t>(15, 128 - max<int16_t>(x - 2, 0)), 3);
    oled.drawBox(max<int16_t>(x - 2, 0), gapBottom,
                 min<int16_t>(15, 128 - max<int16_t>(x - 2, 0)), 3);
  }
}

void drawGameRunning() { render(drawGameRunningFrame); }

void drawGameOverFrame() {
  char score[16];
  snprintf(score, sizeof(score), "SCORE %u", game.score);
  oled.setFont(u8g2_font_6x10_tf);
  centered(14, "SYSTEM CRASHED");
  oled.setFont(u8g2_font_9x15B_tf);
  centered(33, score);
  oled.setFont(u8g2_font_6x10_tf);
  centered(46, game.score >= FLAPPY_REWARD_SCORE ? "HINT UNLOCKED" : "TARGET SCORE 5");
  if (game.score >= FLAPPY_REWARD_SCORE) {
    oled.setFont(u8g2_font_4x6_tf);
    centered(54, MINIGAME_REWARD_LINE_1);
  }
  footer("OK: RETRY  LEFT: EXIT");
}

void drawGameOver() { render(drawGameOverFrame); }

void enterGame() {
  screen = Screen::Game;
  gamePhase = GamePhase::Intro;
  drawGameIntro();
}

void startGame(uint32_t now) {
  gamePhase = GamePhase::Running;
  game.birdY = 28;
  game.velocity = -48;
  game.pipeX = 112;
  game.gapY = random(23, 42);
  game.score = 0;
  game.passed = false;
  game.lastFrame = now;
  drawGameRunning();
}

void updateGame(uint32_t now) {
  if (left.pressed) {
    screen = Screen::Home;
    drawHome();
    return;
  }
  if (gamePhase == GamePhase::Intro) {
    if (ok.pressed) startGame(now);
    return;
  }
  if (gamePhase == GamePhase::Over) {
    if (ok.pressed) startGame(now);
    return;
  }
  if (ok.pressed) game.velocity = -48;
  if (now - game.lastFrame < FLAPPY_FRAME_MS) return;

  const float dt = min<float>((now - game.lastFrame) / 1000.0f, 0.08f);
  game.lastFrame = now;
  game.velocity += 122 * dt;
  game.birdY += game.velocity * dt;
  game.pipeX -= 31 * dt;

  if (!game.passed && game.pipeX + 11 < 28) {
    game.passed = true;
    ++game.score;
    beep(1200, 25);
  }
  if (game.pipeX < -15) {
    game.pipeX = 128;
    game.gapY = random(20, 45);
    game.passed = false;
  }

  if (flappyCollision(game.birdY, game.pipeX, game.gapY)) {
    gamePhase = GamePhase::Over;
    beep(180, 180);
    drawGameOver();
    return;
  }
  drawGameRunning();
}

void resetFirewallBricks() {
  for (uint8_t row = 0; row < FIREWALL_ROWS; ++row) {
    for (uint8_t col = 0; col < FIREWALL_COLS; ++col) {
      firewall.bricks[row][col] = true;
    }
  }
  firewall.remaining = FIREWALL_ROWS * FIREWALL_COLS;
}

void drawFirewallIntroFrame() {
  header("FIREWALL BREAKER");
  oled.setFont(u8g2_font_6x10_tf);
  centered(31, "PRESS OK");
  oled.setFont(u8g2_font_5x7_tf);
  centered(45, "DESTROY THE WALL");
  footer("HOLD OK: EXIT");
}

void drawFirewallIntro() { render(drawFirewallIntroFrame); }

void drawFirewallRunningFrame() {
  for (uint8_t row = 0; row < FIREWALL_ROWS; ++row) {
    for (uint8_t col = 0; col < FIREWALL_COLS; ++col) {
      if (!firewall.bricks[row][col]) continue;
      const int16_t x = FIREWALL_BRICK_X +
                        col * (FIREWALL_BRICK_W + FIREWALL_BRICK_GAP_X);
      const int16_t y = FIREWALL_BRICK_Y +
                        row * (FIREWALL_BRICK_H + FIREWALL_BRICK_GAP_Y);
      oled.drawBox(x, y, FIREWALL_BRICK_W, FIREWALL_BRICK_H);
    }
  }
  oled.drawBox(static_cast<uint8_t>(firewall.ballX),
               static_cast<uint8_t>(firewall.ballY),
               FIREWALL_BALL_SIZE, FIREWALL_BALL_SIZE);
  oled.drawBox(static_cast<uint8_t>(firewall.paddleX), FIREWALL_PADDLE_Y,
               FIREWALL_PADDLE_W, FIREWALL_PADDLE_H);
}

void drawFirewallRunning() { render(drawFirewallRunningFrame); }

void drawFirewallOverFrame() {
  header("FIREWALL ACTIVE");
  oled.setFont(u8g2_font_9x15B_tf);
  centered(34, "ACCESS DENIED");
  oled.setFont(u8g2_font_5x7_tf);
  centered(49, "OK: RETRY");
  footer("HOLD OK: EXIT");
}

void drawFirewallOver() { render(drawFirewallOverFrame); }

void drawFirewallClearFrame() {
  header("FIREWALL BREACHED");
  oled.setFont(u8g2_font_9x15B_tf);
  centered(34, "ACCESS OPEN");
  oled.setFont(u8g2_font_5x7_tf);
  centered(49, "OK: RETRY");
  footer("HOLD OK: EXIT");
}

void drawFirewallClear() { render(drawFirewallClearFrame); }

void enterFirewallGame() {
  screen = Screen::FirewallGame;
  firewall.phase = FirewallPhase::Intro;
  drawFirewallIntro();
}

void startFirewallGame(uint32_t now) {
  firewall.phase = FirewallPhase::Running;
  firewall.ballX = 64;
  firewall.ballY = 46;
  firewall.ballVX = random(0, 2) ? 42 : -42;
  firewall.ballVY = -46;
  firewall.paddleX = (128 - FIREWALL_PADDLE_W) / 2.0f;
  firewall.lastFrame = now;
  resetFirewallBricks();
  drawFirewallRunning();
}

void updateFirewallGame(uint32_t now) {
  if (ok.longPressed) {
    screen = Screen::Home;
    drawHome();
    return;
  }
  if (firewall.phase != FirewallPhase::Running) {
    if (ok.pressed) startFirewallGame(now);
    return;
  }
  if (now - firewall.lastFrame < FIREWALL_FRAME_MS) return;

  const float dt = min<float>((now - firewall.lastFrame) / 1000.0f, 0.06f);
  firewall.lastFrame = now;
  if (left.stable) firewall.paddleX -= FIREWALL_PADDLE_SPEED * dt;
  if (right.stable) firewall.paddleX += FIREWALL_PADDLE_SPEED * dt;
  firewall.paddleX = max<float>(0, min<float>(128 - FIREWALL_PADDLE_W,
                                              firewall.paddleX));

  const float previousY = firewall.ballY;
  firewall.ballX += firewall.ballVX * dt;
  firewall.ballY += firewall.ballVY * dt;
  if (firewall.ballX <= 0) {
    firewall.ballX = 0;
    firewall.ballVX = fabsf(firewall.ballVX);
  } else if (firewall.ballX + FIREWALL_BALL_SIZE >= 128) {
    firewall.ballX = 128 - FIREWALL_BALL_SIZE;
    firewall.ballVX = -fabsf(firewall.ballVX);
  }
  if (firewall.ballY <= 0) {
    firewall.ballY = 0;
    firewall.ballVY = fabsf(firewall.ballVY);
  }

  if (firewall.ballVY > 0 &&
      rectsOverlap(firewall.ballX, firewall.ballY,
                   FIREWALL_BALL_SIZE, FIREWALL_BALL_SIZE,
                   firewall.paddleX, FIREWALL_PADDLE_Y,
                   FIREWALL_PADDLE_W, FIREWALL_PADDLE_H)) {
    firewall.ballY = FIREWALL_PADDLE_Y - FIREWALL_BALL_SIZE;
    firewall.ballVY = -fabsf(firewall.ballVY);
    const float offset = (firewall.ballX + FIREWALL_BALL_SIZE / 2.0f -
                          firewall.paddleX - FIREWALL_PADDLE_W / 2.0f) /
                         (FIREWALL_PADDLE_W / 2.0f);
    firewall.ballVX = max<float>(-70, min<float>(70, firewall.ballVX + offset * 18));
    beep(760, 20);
  }

  bool brickHit = false;
  for (uint8_t row = 0; row < FIREWALL_ROWS && !brickHit; ++row) {
    for (uint8_t col = 0; col < FIREWALL_COLS; ++col) {
      if (!firewall.bricks[row][col]) continue;
      const float x = FIREWALL_BRICK_X +
                      col * (FIREWALL_BRICK_W + FIREWALL_BRICK_GAP_X);
      const float y = FIREWALL_BRICK_Y +
                      row * (FIREWALL_BRICK_H + FIREWALL_BRICK_GAP_Y);
      if (!rectsOverlap(firewall.ballX, firewall.ballY,
                        FIREWALL_BALL_SIZE, FIREWALL_BALL_SIZE,
                        x, y, FIREWALL_BRICK_W, FIREWALL_BRICK_H)) continue;
      firewall.bricks[row][col] = false;
      --firewall.remaining;
      firewall.ballY = previousY;
      firewall.ballVY = -firewall.ballVY;
      brickHit = true;
      beep(1200, 20);
      break;
    }
  }

  if (firewall.remaining == 0) {
    firewall.phase = FirewallPhase::Clear;
    beep(1500, 180);
    drawFirewallClear();
  } else if (firewall.ballY >= 64) {
    firewall.phase = FirewallPhase::Over;
    beep(200, 160);
    drawFirewallOver();
  } else {
    drawFirewallRunning();
  }
}

void updateUi(uint32_t now) {
  left.update(now);
  ok.update(now);
  right.update(now);

  if (screen == Screen::Game) {
    updateGame(now);
    return;
  }
  if (screen == Screen::FirewallGame) {
    updateFirewallGame(now);
    return;
  }

  if (screen == Screen::Home) {
    if (left.pressed) {
      menuItem = (menuItem + HOME_MENU_COUNT - 1) % HOME_MENU_COUNT;
      drawHome();
    } else if (right.pressed) {
      menuItem = (menuItem + 1) % HOME_MENU_COUNT;
      drawHome();
    } else if (ok.pressed) {
      if (menuItem == 0) {
        screen = Screen::Problems;
        drawProblems();
      } else if (menuItem == 1) {
        enterGame();
      } else if (menuItem == 2) {
        enterFirewallGame();
      } else {
        screen = Screen::Status;
        drawStatus();
      }
    }
  } else if (screen == Screen::Problems) {
    if (left.pressed) {
      browserProblem = (browserProblem + SERIAL_PROBLEM_COUNT - 1) % SERIAL_PROBLEM_COUNT;
      drawProblems();
    } else if (right.pressed) {
      browserProblem = (browserProblem + 1) % SERIAL_PROBLEM_COUNT;
      drawProblems();
    } else if (ok.pressed) {
      showProblem(browserProblem);
    }
  } else if ((screen == Screen::Hint || screen == Screen::Status) &&
             ok.longPressed) {
    screen = Screen::Home;
    drawHome();
  } else if (screen == Screen::HiddenGranted && ok.pressed) {
    screen = Screen::Status;
    drawStatus();
  } else if (screen == Screen::Complete && !victory.active && ok.longPressed) {
    screen = Screen::Status;
    drawStatus();
  }
}

bool updateHiddenAccess(uint32_t now) {
  if (isSolved(solvedMask, HIDDEN_ACCESS_INDEX)) return false;

  const bool matched = hiddenAccessMatched(
      digitalRead(Pins::CHALLENGE_1) == LOW,
      digitalRead(Pins::CHALLENGE_2) == LOW);
  if (!matched) {
    hiddenSince = 0;
  } else if (hiddenSince == 0) {
    hiddenSince = now;
  } else if (now - hiddenSince >= HIDDEN_HOLD_MS) {
    solvedMask = markSolved(solvedMask, HIDDEN_ACCESS_INDEX);
    saveMask();
    configureHiddenAccessPins();
    return true;
  }
  return false;
}

const char *screenName() {
  switch (screen) {
    case Screen::Home: return "home";
    case Screen::Problems: return "missions";
    case Screen::Hint: return "hint";
    case Screen::Status: return "status";
    case Screen::Game: return "game";
    case Screen::FirewallGame: return "firewall-game";
    case Screen::HiddenGranted: return "hidden-granted";
    case Screen::Complete: return "complete";
  }
  return "unknown";
}

void bleSendLine(const char *line) {
  if (!bleConnected || bleTx == nullptr) return;
  const size_t length = strlen(line);
  char chunk[BLE_NOTIFY_CHUNK];
  for (size_t offset = 0; offset <= length; offset += BLE_NOTIFY_CHUNK) {
    const size_t remaining = length + 1 - offset;
    const size_t size = min<size_t>(remaining, BLE_NOTIFY_CHUNK);
    for (size_t i = 0; i < size; ++i) {
      const size_t position = offset + i;
      chunk[i] = position == length ? '\n' : line[position];
    }
    bleTx->setValue(reinterpret_cast<uint8_t *>(chunk), size);
    bleTx->notify();
    delay(8);
  }
}

void sendBleStatus() {
  char line[224];
  snprintf(line, sizeof(line),
           "STATUS {\"id\":\"%s\",\"solvedMask\":%u,\"solved\":%u,"
           "\"total\":%u,\"serialSolved\":%u,\"serialProblems\":%u,"
           "\"hiddenSolved\":%s,\"screen\":\"%s\",\"uptimeMs\":%lu}",
           badgeId, solvedMask, solvedCount(),
           static_cast<unsigned>(TOTAL_CHALLENGE_COUNT), serialSolvedCount(),
           static_cast<unsigned>(SERIAL_PROBLEM_COUNT),
           isSolved(solvedMask, HIDDEN_ACCESS_INDEX) ? "true" : "false",
           screenName(), static_cast<unsigned long>(millis()));
  bleSendLine(line);
  bleStatusDirty = false;
}

bool validAdminTag(const char *provided) {
  if (bleChallenge == 0 || strlen(provided) != 14) return false;
  char material[40];
  snprintf(material, sizeof(material), "%s:%08lX", badgeId,
           static_cast<unsigned long>(bleChallenge));
  uint8_t digest[32];
  const mbedtls_md_info_t *sha = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  if (sha == nullptr || mbedtls_md_hmac(
          sha, reinterpret_cast<const uint8_t *>(BLE_ADMIN_KEY),
          strlen(BLE_ADMIN_KEY), reinterpret_cast<const uint8_t *>(material),
          strlen(material), digest) != 0) return false;

  constexpr char hex[] = "0123456789ABCDEF";
  uint8_t different = 0;
  for (uint8_t i = 0; i < 7; ++i) {
    const char high = hex[digest[i] >> 4];
    const char low = hex[digest[i] & 0x0f];
    different |= static_cast<uint8_t>(toupper(provided[i * 2]) ^ high);
    different |= static_cast<uint8_t>(toupper(provided[i * 2 + 1]) ^ low);
  }
  return different == 0;
}

void sendBleHello() {
  bleAuthenticated = false;
  do bleChallenge = esp_random(); while (bleChallenge == 0);
  char line[40];
  snprintf(line, sizeof(line), "HELLO %s %08lX", badgeId,
           static_cast<unsigned long>(bleChallenge));
  bleSendLine(line);
}

class BadgeServerCallbacks final : public BLEServerCallbacks {
  void onConnect(BLEServer *) override {
    bleConnected = true;
    bleAuthenticated = false;
    bleChallenge = 0;
    bleRxLength = 0;
  }

  void onDisconnect(BLEServer *) override {
    bleConnected = false;
    bleAuthenticated = false;
    bleChallenge = 0;
    bleRxLength = 0;
    bleRestartAdvertising = true;
  }
};

class BadgeCommandCallbacks final : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *characteristic) override {
    const std::string value = characteristic->getValue();
    if (value.empty() || bleCommands == nullptr) return;
    for (const char byte : value) {
      if (byte == '\r') continue;
      if (byte == '\n') {
        if (bleRxLength > 0) {
          bleRxLine[bleRxLength] = '\0';
          xQueueSend(bleCommands, bleRxLine, 0);
        }
        bleRxLength = 0;
      } else if (bleRxLength + 1 < sizeof(bleRxLine)) {
        bleRxLine[bleRxLength++] = byte;
      } else {
        bleRxLength = 0;
      }
    }
  }
};

BadgeServerCallbacks badgeServerCallbacks;
BadgeCommandCallbacks badgeCommandCallbacks;

bool decodeField(const char *encoded, char *output, size_t outputSize) {
  if (strcmp(encoded, "-") == 0) {
    output[0] = '\0';
    return true;
  }
  size_t written = 0;
  if (mbedtls_base64_decode(reinterpret_cast<unsigned char *>(output),
                            outputSize - 1, &written,
                            reinterpret_cast<const unsigned char *>(encoded),
                            strlen(encoded)) != 0 ||
      memchr(output, '\0', written) != nullptr) return false;
  output[written] = '\0';
  return true;
}

bool appendField(char *line, size_t &used, const char *value) {
  if (used + 2 >= BLE_COMMAND_MAX) return false;
  line[used++] = '\t';
  if (*value == '\0') {
    line[used++] = '-';
    line[used] = '\0';
    return true;
  }
  size_t written = 0;
  const int result = mbedtls_base64_encode(
      reinterpret_cast<unsigned char *>(line + used), BLE_COMMAND_MAX - used - 1,
      &written, reinterpret_cast<const unsigned char *>(value), strlen(value));
  if (result != 0) return false;
  used += written;
  line[used] = '\0';
  return true;
}

void sendProblem(uint8_t index) {
  const Problem &problem = problems[index];
  char line[BLE_COMMAND_MAX];
  int count = snprintf(line, sizeof(line), "PROBLEM\t%u\t%c\t%u", index + 1,
                       problem.type, problem.optionCount);
  if (count < 0 || static_cast<size_t>(count) >= sizeof(line)) return;
  size_t used = count;
  if (!appendField(line, used, problem.title) ||
      !appendField(line, used, problem.serialText) ||
      !appendField(line, used, problem.answer)) return;
  for (uint8_t i = 0; i < PROBLEM_OPTION_MAX; ++i) {
    if (!appendField(line, used, problem.oledLines[i])) return;
  }
  bleSendLine(line);
}

void setProblem(char *payload) {
  char *save = nullptr;
  char *indexText = strtok_r(payload, "\t", &save);
  char *typeText = strtok_r(nullptr, "\t", &save);
  char *countText = strtok_r(nullptr, "\t", &save);
  if (!indexText || !typeText || !countText) {
    bleSendLine("ERR problem invalid fields");
    return;
  }
  const int number = atoi(indexText);
  if (number < 1 || number > static_cast<int>(SERIAL_PROBLEM_COUNT)) {
    bleSendLine("ERR problem index 1-4 only");
    return;
  }

  Problem candidate{};
  candidate.version = PROBLEM_STORAGE_VERSION;
  candidate.type = typeText[0];
  candidate.optionCount = atoi(countText);
  char *fields[3 + PROBLEM_OPTION_MAX];
  for (char *&field : fields) field = strtok_r(nullptr, "\t", &save);
  if (strtok_r(nullptr, "\t", &save) != nullptr ||
      !fields[0] || !fields[1] || !fields[2] ||
      !decodeField(fields[0], candidate.title, sizeof(candidate.title)) ||
      !decodeField(fields[1], candidate.serialText, sizeof(candidate.serialText)) ||
      !decodeField(fields[2], candidate.answer, sizeof(candidate.answer))) {
    bleSendLine("ERR problem invalid encoding");
    return;
  }
  for (uint8_t i = 0; i < PROBLEM_OPTION_MAX; ++i) {
    if (!fields[3 + i] ||
        !decodeField(fields[3 + i], candidate.oledLines[i],
                     sizeof(candidate.oledLines[i]))) {
      bleSendLine("ERR problem invalid option");
      return;
    }
  }
  if (!validProblem(candidate)) {
    bleSendLine("ERR problem invalid values");
    return;
  }

  const uint8_t index = number - 1;
  problems[index] = candidate;
  saveProblem(index);
  stopVictoryMode();
  solvedMask &= static_cast<uint8_t>(~solvedBit(index));
  saveMask();
  if (usbPlayer.problem == index) resetPlayer(usbPlayer);
  if (blePlayer.problem == index) resetPlayer(blePlayer);
  if (displayedProblem == index) {
    screen = Screen::Problems;
    browserProblem = index;
    drawProblems();
  }
  char response[24];
  snprintf(response, sizeof(response), "OK problem %d", number);
  bleSendLine(response);
  sendProblem(index);
}

void printBleStatus() {
  bleSendLine("[challenge status]");
  char line[64];
  for (uint8_t i = 0; i < SERIAL_PROBLEM_COUNT; ++i) {
    snprintf(line, sizeof(line), "%u. %-13s [%c]", i + 1, problems[i].title,
             isSolved(solvedMask, i) ? 'O' : 'X');
    bleSendLine(line);
  }
}

void handleBleShell(char *command) {
  while (*command == ' ' || *command == '\t') ++command;
  char *end = command + strlen(command);
  while (end > command && (end[-1] == ' ' || end[-1] == '\t')) --end;
  *end = '\0';
  if (*command == '\0') return;

  if (blePlayer.problem >= 0) {
    handleProblemInput(PlayerTarget::Ble, command);
    return;
  }

  if (strlen(command) == 1 && command[0] >= '1' &&
      command[0] < '1' + static_cast<int>(SERIAL_PROBLEM_COUNT)) {
    startProblem(PlayerTarget::Ble, command[0] - '1');
  } else if (strcmp(command, "help") == 0) {
    bleSendLine("USER: 1-4 hint exit status clear aegis");
    bleSendLine("ADMIN: solve all / reset / reboot / problem get 1-4 / dashboard editor");
  } else if (strcmp(command, "hint") == 0) {
    bleSendLine("Select problem 1-4 first.");
  } else if (strcmp(command, "clear") == 0) {
    bleSendLine("CLEAR");
  } else if (strcmp(command, START_COMMAND) == 0) {
    bleSendLine("=== Aegis Hack The Badge / Rev.3 ===");
    bleSendLine("Problems: Serial / choices and examples: OLED");
    bleSendLine("Commands: 1-4 status help hint exit clear aegis");
  } else {
    bleSendLine("ERR unknown command; enter help");
  }
}

void handleBleCommand(char *command) {
  if (strcmp(command, "hello") == 0) {
    sendBleHello();
    return;
  }
  if (strncmp(command, "a ", 2) == 0) {
    if (validAdminTag(command + 2)) {
      bleChallenge = 0;
      bleAuthenticated = true;
      bleSendLine("AUTH OK");
      sendBleStatus();
    } else {
      bleAuthenticated = false;
      bleSendLine("ERR auth");
    }
    return;
  }
  if (!bleAuthenticated) {
    bleSendLine("ERR auth required");
    return;
  }
  if (strcmp(command, "status") == 0) {
    printBleStatus();
    sendBleStatus();
  } else if (strncmp(command, "problem get ", 12) == 0) {
    const int number = atoi(command + 12);
    if (number < 1 || number > static_cast<int>(SERIAL_PROBLEM_COUNT)) {
      bleSendLine("ERR problem index 1-4 only");
    } else {
      sendProblem(number - 1);
    }
  } else if (strncmp(command, "problem set\t", 12) == 0) {
    setProblem(command + 12);
  } else if (strcmp(command, "solve all") == 0) {
    solveAllForAdmin(millis());
    bleSendLine("OK solve all");
    sendBleStatus();
  } else if (strcmp(command, "reset") == 0) {
    resetProgress();
    bleSendLine("OK reset");
    sendBleStatus();
  } else if (strcmp(command, "reboot") == 0) {
    bleSendLine("OK reboot");
    rebootAt = millis() + 250;
  } else {
    handleBleShell(command);
  }
}

void startBleAdmin() {
  const uint64_t mac = ESP.getEfuseMac() & 0xffffffffffffULL;
  snprintf(badgeId, sizeof(badgeId), "AEGIS-%012llX", mac);
  char deviceName[13];
  snprintf(deviceName, sizeof(deviceName), "AEGIS-%06lX",
           static_cast<unsigned long>(mac & 0xffffff));
  bleCommands = xQueueCreate(2, sizeof(BleCommand));
  BLEDevice::init(deviceName);
  bleServer = BLEDevice::createServer();
  bleServer->setCallbacks(&badgeServerCallbacks);
  BLEService *service = bleServer->createService(BLE_SERVICE_UUID);
  bleTx = service->createCharacteristic(
      BLE_TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  bleTx->addDescriptor(new BLE2902());
  BLECharacteristic *rx = service->createCharacteristic(
      BLE_RX_UUID, BLECharacteristic::PROPERTY_WRITE);
  rx->setCallbacks(&badgeCommandCallbacks);
  service->start();
  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_SERVICE_UUID);
  advertising->setScanResponse(true);
  BLEDevice::startAdvertising();
  Serial.printf("BLE admin ready: %s\n", badgeId);
}

void updateBleAdmin(uint32_t now) {
  if (bleRestartAdvertising) {
    bleRestartAdvertising = false;
    if (bleCommands != nullptr) xQueueReset(bleCommands);
    bleRxLength = 0;
    BLEDevice::startAdvertising();
  }
  BleCommand command{};
  while (bleCommands != nullptr &&
         xQueueReceive(bleCommands, &command, 0) == pdTRUE) {
    handleBleCommand(command.text);
  }
  if (bleConnected && bleAuthenticated && bleStatusDirty) sendBleStatus();
  if (rebootAt != 0 && static_cast<int32_t>(now - rebootAt) >= 0) ESP.restart();
}
} // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(Pins::BUZZER, OUTPUT);
  digitalWrite(Pins::BUZZER, LOW);

  for (uint8_t pin : Pins::STATUS_LEDS) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  left.begin();
  ok.begin();
  right.begin();

  oled.setI2CAddress(0x3c << 1);
  oled.setBusClock(400000);
  oled.begin();
  drawBoot();

  preferences.begin("badge", false);
  loadProblems();
  solvedMask = preferences.getUChar("solved", 0) &
               solvedMaskFor(TOTAL_CHALLENGE_COUNT);
  const bool completedAtBoot = allSolved();
  if (!completedAtBoot) updateProgressLeds();

  configureHiddenAccessPins();

  randomSeed(esp_random());
  startBleAdmin();
  printBanner();
  const uint32_t bootAt = millis();
  while (millis() - bootAt < 700) delay(5);
  if (completedAtBoot) {
    enterTrophyModeFromBoot(millis());
  } else {
    drawHome();
    beep(880, 60);
  }
}

void loop() {
  const uint32_t now = millis();
  pollSerial();
  updateBleAdmin(now);
  updateUi(now);
  // Active OLED page와 무관한 전역 하드웨어 이벤트로 감지한다.
  if (updateHiddenAccess(now)) {
    screen = Screen::HiddenGranted;
    drawHiddenGranted();
    beep(1047, 130);
    if (allSolved()) hiddenVictoryAt = now + 750;
  }
  if (hiddenVictoryAt != 0 &&
      static_cast<int32_t>(now - hiddenVictoryAt) >= 0) {
    hiddenVictoryAt = 0;
    startVictorySequence(now);
  }
  updateVictory(now);
  updateTrophyLedSweep(now);
  delay(1);
}

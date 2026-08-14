#include <Arduino.h>
#include <Preferences.h>
#include <U8x8lib.h>
#include <WebServer.h>
#include <WiFi.h>

#include "logic.h"
#include "pins.h"
#include "problems.h"

namespace {
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint32_t BUTTON_DEBOUNCE_MS = 30;
constexpr uint32_t HIDDEN_HOLD_MS = 1200;
constexpr uint32_t ADMIN_BOOT_HOLD_MS = 1500;
constexpr uint16_t REACTION_REWARD_MS = 300;
constexpr char START_COMMAND[] = "aegis";
constexpr char ADMIN_USER[] = "admin";

Preferences preferences;
WebServer server(80);
U8X8_SSD1315_128X64_NONAME_HW_I2C oled(U8X8_PIN_NONE, Pins::OLED_SCL,
                                       Pins::OLED_SDA);

uint8_t solvedMask = 0;
int8_t activeProblem = -1;
uint8_t menuItem = 0;
uint8_t browserProblem = 0;
bool adminEnabled = false;
uint32_t hiddenSince = 0;
char wifiSsid[20] = {};
char wifiPassword[13] = {};
char webPassword[13] = {};
char serialLine[192] = {};
uint8_t serialLength = 0;

enum class Screen : uint8_t { Home, Problems, Hint, Status, Game };
enum class GamePhase : uint8_t { Waiting, Go, Result, TooSoon };
Screen screen = Screen::Home;
GamePhase gamePhase = GamePhase::Waiting;
uint32_t gameAt = 0;
uint16_t lastReactionMs = 0;

struct Button {
  uint8_t pin;
  bool stable = false;
  bool raw = false;
  bool pressed = false;
  uint32_t changedAt = 0;

  explicit Button(uint8_t buttonPin) : pin(buttonPin) {}

  void begin() {
    pinMode(pin, INPUT_PULLUP);
    stable = raw = digitalRead(pin) == LOW;
  }

  void update(uint32_t now) {
    pressed = false;
    const bool next = digitalRead(pin) == LOW;
    if (next != raw) {
      raw = next;
      changedAt = now;
    }
    if (raw != stable && now - changedAt >= BUTTON_DEBOUNCE_MS) {
      stable = raw;
      pressed = stable;
    }
  }
};

Button left{Pins::BUTTON_LEFT};
Button ok{Pins::BUTTON_OK};
Button right{Pins::BUTTON_RIGHT};

void line(uint8_t row, const char *text) {
  oled.clearLine(row);
  oled.drawString(0, row, text);
}

uint8_t solvedCount() {
  uint8_t count = 0;
  for (uint8_t i = 0; i < TOTAL_CHALLENGE_COUNT; ++i) {
    count += isSolved(solvedMask, i);
  }
  return count;
}

bool allSolved() {
  return (solvedMask & solvedMaskFor(TOTAL_CHALLENGE_COUNT)) ==
         solvedMaskFor(TOTAL_CHALLENGE_COUNT);
}

void updateLeds() {
  for (uint8_t i = 0; i < TOTAL_CHALLENGE_COUNT; ++i) {
    digitalWrite(Pins::STATUS_LEDS[i], isSolved(solvedMask, i) ? HIGH : LOW);
  }
}

void saveMask() {
  preferences.putUChar("solved", solvedMask);
  updateLeds();
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

void drawHome() {
  static const char *const items[] = {"Problems", "Mini game", "Status"};
  char progress[17];
  snprintf(progress, sizeof(progress), "Solved %u/%u", solvedCount(),
           static_cast<unsigned>(TOTAL_CHALLENGE_COUNT));
  oled.clearDisplay();
  line(0, "AEGIS HACK BADGE");
  line(2, progress);
  line(4, items[menuItem]);
  line(7, "<      OK      >");
}

void drawProblems() {
  char number[17];
  snprintf(number, sizeof(number), "Problem %u/%u %c",
           static_cast<unsigned>(browserProblem + 1),
           static_cast<unsigned>(SERIAL_PROBLEM_COUNT),
           isSolved(solvedMask, browserProblem) ? 'O' : 'X');
  oled.clearDisplay();
  line(0, "SERIAL PROBLEMS");
  line(2, number);
  line(4, PROBLEMS[browserProblem].title);
  line(7, "<  OK:show   >");
}

void drawHint(uint8_t index) {
  oled.clearDisplay();
  line(0, PROBLEMS[index].title);
  for (uint8_t row = 0; row < 5; ++row) {
    line(row + 2, PROBLEMS[index].oledLines[row]);
  }
  line(7, "OK: menu");
}

void drawStatus() {
  char row[17];
  oled.clearDisplay();
  line(0, allSolved() ? "ALL CLEAR" : "BADGE STATUS");
  for (uint8_t i = 0; i < TOTAL_CHALLENGE_COUNT; ++i) {
    snprintf(row, sizeof(row), "%u:%c %s", i + 1,
             isSolved(solvedMask, i) ? 'O' : 'X',
             i == HIDDEN_ACCESS_INDEX ? "Hidden" : PROBLEMS[i].title);
    line(i + 1, row);
  }
  line(7, "OK: menu");
}

void printBanner() {
  Serial.println();
  Serial.println(F("=== Aegis Hack The Badge / Rev.3 ==="));
  Serial.println(F("문제 본문: Serial / 보기와 예시: OLED"));
  Serial.println(F("명령: 1-4, status, help, hint, exit, clear, reset, aegis"));
  Serial.println(F("Hidden Access는 번호 선택형 문제가 아닙니다."));
}

void printStatus() {
  Serial.println(F("\n[challenge status]"));
  for (uint8_t i = 0; i < TOTAL_CHALLENGE_COUNT; ++i) {
    Serial.printf("%u. %-13s [%c]\n", i + 1,
                  i == HIDDEN_ACCESS_INDEX ? "Hidden Access" : PROBLEMS[i].title,
                  isSolved(solvedMask, i) ? 'O' : 'X');
  }
}

void showProblem(uint8_t index) {
  activeProblem = index;
  screen = Screen::Hint;
  drawHint(index);
  Serial.println();
  Serial.println(PROBLEMS[index].serialText);
  Serial.println(F("\n보기/예시는 OLED를 확인하세요. FLAG 또는 exit를 입력하세요."));
  beep(659);
}

void solved(uint8_t index) {
  const uint8_t next = markSolved(solvedMask, index);
  if (next != solvedMask) {
    solvedMask = next;
    saveMask();
  }
  Serial.printf("정답입니다. 진행도: %u/%u\n", solvedCount(),
                static_cast<unsigned>(TOTAL_CHALLENGE_COUNT));
  beep(1047, 130);
  activeProblem = -1;
  screen = Screen::Status;
  drawStatus();
}

void handleSerialLine(char *input) {
  while (*input == ' ' || *input == '\t') ++input;
  char *end = input + strlen(input);
  while (end > input && (end[-1] == ' ' || end[-1] == '\t')) --end;
  *end = '\0';
  if (*input == '\0') return;

  if (activeProblem >= 0) {
    if (strcmp(input, "exit") == 0) {
      activeProblem = -1;
      screen = Screen::Home;
      drawHome();
      Serial.println(F("문제에서 나왔습니다."));
    } else if (strcmp(input, "hint") == 0) {
      drawHint(activeProblem);
      Serial.println(F("OLED에 보기/예시를 다시 표시했습니다."));
    } else if (strcmp(input, PROBLEMS[activeProblem].answer) == 0) {
      solved(activeProblem);
    } else {
      Serial.println(F("정답이 아닙니다. 다시 시도하거나 exit를 입력하세요."));
      beep(196, 150);
    }
    return;
  }

  if (strlen(input) == 1 && input[0] >= '1' &&
      input[0] < '1' + static_cast<int>(SERIAL_PROBLEM_COUNT)) {
    showProblem(input[0] - '1');
  } else if (strcmp(input, "status") == 0) {
    printStatus();
  } else if (strcmp(input, "help") == 0) {
    Serial.println(F("1-4 중 하나를 선택하고 Serial에 FLAG를 제출하세요."));
    Serial.println(F("문제의 보기/예시는 OLED에만 표시됩니다."));
    Serial.println(F("OLED 미니게임은 하단 3개 버튼으로 플레이합니다."));
  } else if (strcmp(input, "hint") == 0) {
    Serial.println(F("먼저 1-4 중 문제를 선택하세요."));
  } else if (strcmp(input, "clear") == 0) {
    for (uint8_t i = 0; i < 30; ++i) Serial.println();
  } else if (strcmp(input, "reset") == 0) {
    solvedMask = 0;
    saveMask();
    configureHiddenAccessPins();
    activeProblem = -1;
    screen = Screen::Home;
    drawHome();
    Serial.println(F("진행 상태를 초기화했습니다."));
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

void startReactionGame() {
  screen = Screen::Game;
  gamePhase = GamePhase::Waiting;
  gameAt = millis() + random(1200, 3501);
  oled.clearDisplay();
  line(0, "REACTION TEST");
  line(3, "WAIT...");
  line(7, "do not press");
}

void showGameResult() {
  char score[17];
  snprintf(score, sizeof(score), "%u ms", lastReactionMs);
  oled.clearDisplay();
  line(0, "REACTION RESULT");
  line(2, score);
  if (lastReactionMs <= REACTION_REWARD_MS) {
    line(4, MINIGAME_REWARD_LINE_1);
    line(5, MINIGAME_REWARD_LINE_2);
  }
  line(7, "OK:again <>:exit");
}

void updateGame(uint32_t now) {
  if (gamePhase == GamePhase::Waiting) {
    if (left.pressed || ok.pressed || right.pressed) {
      gamePhase = GamePhase::TooSoon;
      gameAt = now;
      oled.clearDisplay();
      line(2, "TOO SOON!");
      line(5, "OK: retry");
      beep(180, 180);
    } else if (static_cast<int32_t>(now - gameAt) >= 0) {
      gamePhase = GamePhase::Go;
      gameAt = now;
      oled.clearDisplay();
      line(2, "PRESS OK NOW!");
      beep(1200, 35);
    }
  } else if (gamePhase == GamePhase::Go && ok.pressed) {
    const uint32_t elapsed = now - gameAt;
    lastReactionMs = static_cast<uint16_t>(elapsed > 9999 ? 9999 : elapsed);
    gamePhase = GamePhase::Result;
    showGameResult();
  } else if ((gamePhase == GamePhase::Result || gamePhase == GamePhase::TooSoon) &&
             ok.pressed) {
    startReactionGame();
  } else if ((gamePhase == GamePhase::Result || gamePhase == GamePhase::TooSoon) &&
             (left.pressed || right.pressed)) {
    screen = Screen::Home;
    drawHome();
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

  if (screen == Screen::Home) {
    if (left.pressed) {
      menuItem = (menuItem + 2) % 3;
      drawHome();
    } else if (right.pressed) {
      menuItem = (menuItem + 1) % 3;
      drawHome();
    } else if (ok.pressed) {
      if (menuItem == 0) {
        screen = Screen::Problems;
        drawProblems();
      } else if (menuItem == 1) {
        startReactionGame();
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
  } else if (ok.pressed) {
    screen = Screen::Home;
    drawHome();
  }
}

void updateHiddenAccess(uint32_t now) {
  if (isSolved(solvedMask, HIDDEN_ACCESS_INDEX)) return;

  const bool matched = hiddenAccessMatched(digitalRead(Pins::CHALLENGE_1) == LOW,
                                           digitalRead(Pins::CHALLENGE_2) == LOW);
  if (!matched) {
    hiddenSince = 0;
  } else if (hiddenSince == 0) {
    hiddenSince = now;
  } else if (now - hiddenSince >= HIDDEN_HOLD_MS) {
    solvedMask = markSolved(solvedMask, HIDDEN_ACCESS_INDEX);
    saveMask();
    configureHiddenAccessPins();
    Serial.println(F("\n[Hidden Access] unlocked."));
    screen = Screen::Status;
    drawStatus();
    beep(1568, 180);
  }
}

bool adminAuth() {
  if (server.authenticate(ADMIN_USER, webPassword)) return true;
  server.requestAuthentication();
  return false;
}

const char ADMIN_HTML[] PROGMEM = R"HTML(
<!doctype html><meta name=viewport content="width=device-width">
<title>Aegis Badge Admin</title>
<style>body{font:16px system-ui;max-width:36rem;margin:2rem auto;padding:0 1rem}button{padding:.7rem;margin:.25rem}pre{background:#eee;padding:1rem}</style>
<h1>Aegis Badge Admin</h1><pre id=s>loading...</pre>
<div id=b></div><button onclick="post('/api/reset')">Reset all</button>
<button onclick="post('/api/reboot')">Reboot</button>
<script>
async function load(){let r=await fetch('/api/status');let j=await r.json();s.textContent=JSON.stringify(j,null,2);b.innerHTML='';for(let i=1;i<=j.total;i++)b.innerHTML+=`<button onclick="post('/api/solve?id=${i}')">Solve ${i}</button>`}
async function post(u){await fetch(u,{method:'POST'});setTimeout(load,200)}load()
</script>)HTML";

void sendAdminStatus() {
  if (!adminAuth()) return;
  char json[192];
  snprintf(json, sizeof(json),
           "{\"solvedMask\":%u,\"solved\":%u,\"total\":%u,"
           "\"serialProblems\":%u,\"hiddenSolved\":%s}",
           solvedMask, solvedCount(), static_cast<unsigned>(TOTAL_CHALLENGE_COUNT),
           static_cast<unsigned>(SERIAL_PROBLEM_COUNT),
           isSolved(solvedMask, HIDDEN_ACCESS_INDEX) ? "true" : "false");
  server.send(200, "application/json", json);
}

void setupAdminRoutes() {
  server.on("/", HTTP_GET, [] {
    if (adminAuth()) server.send_P(200, "text/html", ADMIN_HTML);
  });
  server.on("/api/status", HTTP_GET, sendAdminStatus);
  server.on("/api/solve", HTTP_POST, [] {
    if (!adminAuth()) return;
    const int id = server.arg("id").toInt();
    if (id < 1 || id > static_cast<int>(TOTAL_CHALLENGE_COUNT)) {
      server.send(400, "application/json", "{\"error\":\"bad id\"}");
      return;
    }
    solvedMask = markSolved(solvedMask, id - 1);
    saveMask();
    configureHiddenAccessPins();
    screen = Screen::Status;
    drawStatus();
    server.send(200, "application/json", "{\"ok\":true}");
  });
  server.on("/api/reset", HTTP_POST, [] {
    if (!adminAuth()) return;
    solvedMask = 0;
    saveMask();
    configureHiddenAccessPins();
    activeProblem = -1;
    screen = Screen::Status;
    drawStatus();
    server.send(200, "application/json", "{\"ok\":true}");
  });
  server.on("/api/reboot", HTTP_POST, [] {
    if (!adminAuth()) return;
    server.send(200, "application/json", "{\"ok\":true}");
    delay(100);
    ESP.restart();
  });
  server.onNotFound([] {
    if (adminAuth()) server.send(404, "text/plain", "not found");
  });
}

void randomCredential(char *output, size_t length) {
  constexpr char alphabet[] = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  for (size_t i = 0; i + 1 < length; ++i) {
    output[i] = alphabet[esp_random() % (sizeof(alphabet) - 1)];
  }
  output[length - 1] = '\0';
}

bool adminChordHeld() {
  const uint32_t start = millis();
  while (millis() - start < ADMIN_BOOT_HOLD_MS) {
    if (digitalRead(Pins::BUTTON_LEFT) != LOW ||
        digitalRead(Pins::BUTTON_RIGHT) != LOW) return false;
    delay(10);
  }
  return true;
}

void startAdmin() {
  const uint64_t mac = ESP.getEfuseMac();
  snprintf(wifiSsid, sizeof(wifiSsid), "AegisBadge-%04X",
           static_cast<unsigned>(mac & 0xffff));
  randomCredential(wifiPassword, sizeof(wifiPassword));
  randomCredential(webPassword, sizeof(webPassword));

  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP(wifiSsid, wifiPassword)) {
    Serial.println(F("Admin AP start failed."));
    return;
  }
  setupAdminRoutes();
  server.begin();
  adminEnabled = true;

  oled.clearDisplay();
  line(0, "ADMIN WIFI ON");
  line(1, wifiSsid);
  line(2, "WiFi password:");
  line(3, wifiPassword);
  line(4, "user: admin");
  line(5, "web password:");
  line(6, webPassword);
  line(7, "192.168.4.1");

  Serial.printf("\nAdmin AP: %s\nWiFi password: %s\n", wifiSsid, wifiPassword);
  Serial.printf("URL: http://192.168.4.1 / user: %s / password: %s\n",
                ADMIN_USER, webPassword);
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
  oled.setFont(u8x8_font_chroma48medium8_r);

  preferences.begin("badge", false);
  solvedMask = preferences.getUChar("solved", 0) &
               solvedMaskFor(TOTAL_CHALLENGE_COUNT);
  updateLeds();

  configureHiddenAccessPins();

  randomSeed(esp_random());
  printBanner();
  if (adminChordHeld()) {
    startAdmin();
  } else {
    drawHome();
  }
  beep(880, 60);
}

void loop() {
  const uint32_t now = millis();
  pollSerial();
  updateUi(now);
  updateHiddenAccess(now);
  if (adminEnabled) server.handleClient();
  delay(1);
}

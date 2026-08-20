# AEGIS Hack The Badge — Breakout & Trophy Mode Implementation Spec

> Repository: `dkuaegis/aegis-hack-the-badge`  
> Target: ESP32-S3 firmware / 128×64 OLED / 3-button input / 5 status LEDs / buzzer  
> Purpose: Codex가 기존 Hack The Badge 펌웨어에 **FIREWALL BREAKER(Breakout)** 미니게임과 **All Solved Trophy Mode**를 안정적으로 추가하기 위한 구현 명세  
> Important: 기존 4개 Serial Mission + Hidden Access 구조, BLE Admin, Flappy Hacker는 유지한다.

---

# 1. 작업 목표

이번 작업은 크게 두 가지다.

## A. 새로운 보너스 미니게임 추가

기존 `FLAPPY HACKER` 옆에 Breakout 계열 게임을 추가한다.

최종 이름:

```text
FIREWALL BREAKER
```

게임 컨셉:

```text
상단의 FIREWALL 벽돌을
하단 패들과 공으로 전부 파괴한다.
```

이 게임은 **Challenge가 아니다.**

따라서:

```text
Serial Missions 4
+ Hidden Access 1
= TOTAL_CHALLENGE_COUNT 5
```

구조는 절대 변경하지 않는다.

미니게임은 순수 보너스/Easter Egg 기능이다.

---

## B. All Solved Trophy Mode 추가

5개의 Challenge를 모두 해결하면 기존의 단순 Complete 화면 대신 Trophy Mode로 전환한다.

OLED:

```text
     Congratulations!

      AEGIS{PWN3D!}

 You solved all problems XD
```

실제 128×64 화면에서는 폰트 크기와 폭에 맞춰 중앙 정렬한다.

핵심은 가운데:

```text
AEGIS{PWN3D!}
```

를 가능한 한 **크고 굵게(Bold)** 보여주는 것이다.

마지막 문제를 막 해결한 순간에는:

```text
ALL SOLVED
   ↓
Victory event
   ↓
Victory melody
   ↓
Trophy screen
   ↓
event 종료
   ↓
5개 LED 왕복 애니메이션
```

으로 동작한다.

이미 5/5 상태인 배지를 재부팅하면:

```text
Boot Logo
   ↓
NVS solvedMask 확인
   ↓
allSolved() == true
   ↓
Trophy screen 복원
   ↓
LED 왕복 애니메이션
```

으로 들어간다.

재부팅할 때마다 우승 멜로디를 반복 재생하지 않는다.

---

# 2. 현재 코드와의 관계

현재 기본 구조에는 다음 요소가 이미 존재한다.

```cpp
enum class Screen : uint8_t {
  Home, Problems, Hint, Status, Game, HiddenGranted, Complete
};

enum class GamePhase : uint8_t {
  Intro, Running, Over
};
```

기존 홈 메뉴:

```cpp
static const char *const items[] = {
  "MISSIONS",
  "FLAPPY HACKER",
  "STATUS"
};
```

기존 Complete 화면:

```text
ALL CLEAR
ACCESS ELEVATED
AEGIS{PWNED}
```

기존 LED는 각 Challenge solved bit를 표현한다.

이번 작업에서:

- 기존 Flappy 기능은 유지
- 기존 `Game`은 Flappy용으로 유지해도 됨
- Breakout용 Screen/State를 추가
- `Complete`는 Trophy 화면으로 변경
- all-solved 상태에서는 STATUS LED 의미를 Trophy Animation으로 override

한다.

---

# 3. 전체 UX

최종 홈 메뉴:

```text
MISSIONS
FLAPPY HACKER
FIREWALL BREAKER
STATUS
```

메뉴 순서는 위와 같이 한다.

### 조작

| 화면 | LEFT | OK | RIGHT |
|---|---|---|---|
| Home | 이전 메뉴 | 선택 | 다음 메뉴 |
| Flappy Intro | Exit | Start | - |
| Flappy Running | Exit | Flap | - |
| Firewall Intro | - | Start | - |
| Firewall Running | Paddle Left | - | Paddle Right |
| Firewall Game Over | - | Retry | - |
| Firewall Clear | - | Retry | - |
| Firewall 모든 상태 | - | **Hold OK = Exit** | - |
| Trophy | 선택적 | 선택적 | 선택적 |

Breakout에서는 LEFT/RIGHT가 패들 조작에 필요하므로 기존 Flappy처럼 LEFT를 Exit로 사용하면 안 된다.

따라서 FIREWALL BREAKER의 종료는:

```text
HOLD OK: EXIT
```

로 통일한다.

---

# 4. Screen 구조 수정

가장 적은 변경으로 구현한다.

권장:

```cpp
enum class Screen : uint8_t {
  Home,
  Problems,
  Hint,
  Status,
  Game,            // 기존 Flappy Hacker 유지
  FirewallGame,    // 신규
  HiddenGranted,
  Complete
};
```

기존 `Screen::Game`을 `FlappyGame`으로 rename해도 되지만 불필요한 diff가 커진다면 유지한다.

BLE status에서 사용하는 `screenName()`에도 반드시 추가한다.

예:

```cpp
case Screen::FirewallGame:
  return "firewall-game";
```

---

# 5. Home Menu 수정

기존 3개 메뉴를 4개로 변경한다.

```cpp
static const char *const items[] = {
  "MISSIONS",
  "FLAPPY HACKER",
  "FIREWALL BREAKER",
  "STATUS"
};
```

magic number `3`을 직접 사용하지 않는다.

예:

```cpp
constexpr uint8_t HOME_MENU_COUNT = 4;
```

OK:

```text
0 -> Problems
1 -> Flappy Hacker
2 -> Firewall Breaker
3 -> Status
```

---

# 6. FIREWALL BREAKER 게임 디자인

## 6.1 화면 컨셉

128×64 OLED:

```text
┌──────────────────────────────┐
│ ■ ■ ■ ■ ■ ■ ■ ■            │
│ ■ ■ ■ ■ ■ ■ ■ ■            │
│ ■ ■ ■ ■ ■ ■ ■ ■            │
│                              │
│             ●                │
│                              │
│          ━━━━━               │
└──────────────────────────────┘
```

게임 화면에 복잡한 텍스트를 넣지 않는다.

---

# 7. Breakout 상태 구조

Flappy와 상태를 분리한다.

```cpp
enum class FirewallPhase : uint8_t {
  Intro,
  Running,
  Over,
  Clear
};

struct FirewallState {
  FirewallPhase phase = FirewallPhase::Intro;

  float ballX = 64.0f;
  float ballY = 45.0f;
  float ballVX = 42.0f;
  float ballVY = -46.0f;

  float paddleX = 52.0f;

  bool bricks[FIREWALL_ROWS][FIREWALL_COLS] = {};
  uint8_t remaining = 0;

  uint32_t lastFrame = 0;
};
```

---

# 8. 권장 Breakout 상수

```cpp
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
```

실제 Wokwi/하드웨어에서 감각을 보고 조정 가능.

---

# 9. Brick Layout

3 × 8 = 24개의 벽돌.

초기화:

```cpp
for (uint8_t row = 0; row < FIREWALL_ROWS; ++row) {
  for (uint8_t col = 0; col < FIREWALL_COLS; ++col) {
    firewall.bricks[row][col] = true;
  }
}

firewall.remaining = FIREWALL_ROWS * FIREWALL_COLS;
```

---

# 10. Breakout Intro

화면:

```text
FIREWALL BREAKER

PRESS OK

HOLD OK: EXIT
```

OK short press:

```text
startFirewallGame(now)
```

OK long press:

```text
Home
```

---

# 11. 게임 시작

`startFirewallGame(now)`에서 전체 state를 초기화한다.

```cpp
firewall.phase = FirewallPhase::Running;

firewall.ballX = 64.0f;
firewall.ballY = 46.0f;
firewall.ballVX = random(0, 2) ? 42.0f : -42.0f;
firewall.ballVY = -46.0f;

firewall.paddleX =
    (128 - FIREWALL_PADDLE_W) / 2.0f;

resetFirewallBricks();

firewall.lastFrame = now;
```

---

# 12. Paddle 조작

Running 상태에서 버튼 hold를 사용한다.

```cpp
if (left.stable) {
  firewall.paddleX -= FIREWALL_PADDLE_SPEED * dt;
}

if (right.stable) {
  firewall.paddleX += FIREWALL_PADDLE_SPEED * dt;
}
```

`pressed` 이벤트만 사용하지 않는다.

화면 밖으로 나가지 않게 clamp한다.

---

# 13. Ball 이동 / Wall collision

```cpp
firewall.ballX += firewall.ballVX * dt;
firewall.ballY += firewall.ballVY * dt;
```

LEFT/RIGHT/TOP wall 충돌 시 해당 velocity 반전.

공이 아래로 완전히 빠지면:

```cpp
firewall.phase = FirewallPhase::Over;
```

---

# 14. Paddle 충돌

AABB 충돌로 충분하다.

충돌 시:

```cpp
firewall.ballVY = -fabsf(firewall.ballVY);
```

공이 paddle 내부에 박히지 않도록 위치 보정.

선택적으로 hit 위치에 따라 `ballVX`를 약간 변경해 조작감을 개선한다.

---

# 15. Brick 충돌

활성 brick과 충돌하면:

```text
brick inactive
remaining--
ballVY 반전
short beep
```

한 프레임에 여러 brick을 동시에 제거하지 않도록 첫 충돌 후 빠져나온다.

---

# 16. Clear / Game Over

Clear:

```text
FIREWALL
BREACHED

ACCESS OPEN

OK: RETRY
HOLD OK: EXIT
```

Game Over:

```text
FIREWALL ACTIVE

ACCESS DENIED

OK: RETRY
HOLD OK: EXIT
```

이 게임은 Challenge가 아니므로:

- solvedMask 변경 금지
- STATUS LED 변경 금지
- FLAG 지급 금지

---

# 17. Breakout Sound

기존 `beep()` 사용.

권장:

```text
Paddle collision -> 700~800 Hz / 15~25ms
Brick destroyed  -> 1000~1300 Hz / 15~25ms
Game over        -> 180~220 Hz / 150ms
Clear            -> 짧은 상승음
```

---

# 18. Breakout 함수 구성

```cpp
void resetFirewallBricks();
void enterFirewallGame();
void startFirewallGame(uint32_t now);

void drawFirewallIntro();
void drawFirewallRunning();
void drawFirewallOver();
void drawFirewallClear();

void updateFirewallGame(uint32_t now);
```

`updateUi()` 안에 물리 코드를 몰아넣지 않는다.

---

# 19. Trophy Mode 화면

기존 `drawCompleteFrame()`을 교체한다.

최종 내용:

```text
Congratulations!

AEGIS{PWN3D!}

You solved all problems XD
```

가운데 `AEGIS{PWN3D!}`가 가장 눈에 띄어야 한다.

---

# 20. Trophy OLED 폰트

Top:

```cpp
u8g2_font_5x7_tf
```

Center:

```cpp
u8g2_font_9x15B_tf
```

폭이 126px을 넘으면 실제 존재하는 더 작은 Bold 폰트로 fallback.

Bottom:

```cpp
u8g2_font_4x6_tf
```

반드시 `oled.getStrWidth()`로 확인한다.

예:

```cpp
oled.setFont(u8g2_font_9x15B_tf);

if (oled.getStrWidth("AEGIS{PWN3D!}") > 126) {
  // 실제 존재하는 더 작은 Bold font 선택
}
```

---

# 21. Trophy layout 예시

```cpp
void drawCompleteFrame() {
  oled.setFont(u8g2_font_5x7_tf);
  centered(8, "Congratulations!");

  oled.setFont(u8g2_font_9x15B_tf);
  centered(37, "AEGIS{PWN3D!}");

  oled.setFont(u8g2_font_4x6_tf);
  centered(59, "You solved all problems XD");
}
```

정확한 baseline은 실제 OLED에서 조정.

border/footer는 넣지 않는다.

---

# 22. Victory State

Trophy 화면과 Victory event를 분리한다.

```cpp
enum class VictoryPhase : uint8_t {
  Idle,
  FlashOn1,
  FlashOff1,
  FlashOn2,
  Fanfare,
  TrophyIdle
};

struct VictoryState {
  VictoryPhase phase = VictoryPhase::Idle;

  bool active = false;
  bool ledSweep = false;

  uint8_t melodyIndex = 0;
  uint32_t nextAt = 0;

  int8_t ledPosition = 0;
  int8_t ledDirection = 1;
  uint32_t ledNextAt = 0;
};
```

---

# 23. allSolved transition 감지

단순히 loop에서 `allSolved()`를 보고 이벤트를 시작하지 않는다.

반드시:

```text
false -> true
```

transition일 때만 full victory event를 시작한다.

Challenge solved 처리를 중앙화하는 것을 권장한다.

---

# 24. Hidden Access가 마지막일 때

필수 케이스:

```text
Serial 1~4 solved
Hidden unsolved
   ↓
C0-C2 해결
   ↓
5/5
   ↓
Victory Sequence
```

기존 Hidden Granted 화면에 영구적으로 멈추면 안 된다.

Hidden Granted를 600~900ms 정도 보여주고 Victory로 넘어가도 되지만 **blocking delay는 금지**.

---

# 25. Serial Mission이 마지막일 때

정답 처리 후 5/5가 되면:

```text
정답입니다.
↓
startVictorySequence()
```

기존 단순 `drawComplete()` 호출만 하지 않는다.

---

# 26. Victory Event OLED

마지막 문제를 해결한 즉시 Trophy 화면을 표시한다.

멜로디가 재생되는 동안에도 OLED는 이미:

```text
Congratulations!
AEGIS{PWN3D!}
You solved all problems XD
```

를 보여준다.

OLED 자체를 빠르게 깜빡이지 않는다.

---

# 27. Victory LED Event

초기:

```text
● ● ● ● ●  250ms
○ ○ ○ ○ ○  120ms
● ● ● ● ●  250ms
```

이후 fanfare.

Victory event 종료 후 왕복 애니메이션으로 전환.

---

# 28. Victory Melody

저작권 있는 게임 멜로디를 복제하지 말고 짧은 자체 8-bit fanfare 사용.

예:

```cpp
struct VictoryNote {
  uint16_t frequency;
  uint16_t duration;
  uint16_t gap;
};

constexpr VictoryNote VICTORY_MELODY[] = {
  {523,  90, 25},
  {659,  90, 25},
  {784,  90, 25},
  {1047, 180, 40},
  {784,  90, 25},
  {1047, 90, 25},
  {1319, 140, 30},
  {1568, 360, 0},
};
```

---

# 29. Melody는 non-blocking

금지:

```cpp
tone(...);
delay(...);
tone(...);
delay(...);
```

권장:

```cpp
void updateVictoryMelody(uint32_t now);
```

`millis()` 기반 scheduler로 각 note를 재생한다.

BLE/Serial/UI loop를 막지 않는다.

---

# 30. Victory Event 종료

마지막 note가 끝나면:

```cpp
victory.active = false;
victory.ledSweep = true;
victory.phase = VictoryPhase::TrophyIdle;
```

OLED Trophy 화면은 유지.

---

# 31. LED 왕복 애니메이션

5개 LED:

```text
● ○ ○ ○ ○
○ ● ○ ○ ○
○ ○ ● ○ ○
○ ○ ○ ● ○
○ ○ ○ ○ ●
○ ○ ○ ● ○
○ ○ ● ○ ○
○ ● ○ ○ ○
● ○ ○ ○ ○
...
```

권장 step:

```cpp
constexpr uint32_t TROPHY_LED_STEP_MS = 120;
```

---

# 32. Progress LED / Trophy LED 분리

기존 solved progress 표시와 Trophy animation이 서로 덮어쓰지 않도록 모드를 분리한다.

예:

```cpp
enum class LedMode : uint8_t {
  Progress,
  VictoryEvent,
  TrophySweep
};
```

또는 `VictoryState` flags로 처리 가능.

핵심:

```text
Normal -> solvedMask progress LEDs
Victory -> victory control
Complete idle -> sweep
```

---

# 33. 부팅 직후 allSolved 체크

NVS에서 solvedMask를 읽은 뒤:

```cpp
const bool completedAtBoot = allSolved();
```

Boot logo 표시 후:

```cpp
if (completedAtBoot) {
  enterTrophyModeFromBoot(millis());
} else {
  updateProgressLeds();
  drawHome();
}
```

---

# 34. Boot Trophy Mode

이미 5/5로 부팅된 경우:

- Victory Melody 재생하지 않음
- 전체 LED flash 생략
- Trophy OLED 표시
- LED sweep 시작

예:

```cpp
void enterTrophyModeFromBoot(uint32_t now) {
  screen = Screen::Complete;
  drawComplete();

  victory.active = false;
  victory.phase = VictoryPhase::TrophyIdle;
  victory.ledSweep = true;
  victory.ledPosition = 0;
  victory.ledDirection = 1;
  victory.ledNextAt = now;
}
```

---

# 35. 마지막 문제 직후 full Victory

`startVictorySequence(now)`:

```text
1. activeProblem reset
2. Screen::Complete
3. Trophy OLED draw
4. Serial 축하 메시지
5. LED flash
6. melody 시작
7. event 종료 후 sweep
```

---

# 36. Serial 축하 메시지

Serial/Web Console에는 한국어.

예:

```text
================================
   모든 문제를 해결했습니다!
================================

축하합니다!
AEGIS Hack The Badge의 모든 Challenge를 완료했습니다.

AEGIS{PWN3D!}
```

마지막 solve 직후 한 번만 출력.

---

# 37. Trophy 화면 유지

Victory event가 끝나도 OLED는 Trophy 화면을 계속 유지한다.

자동으로 Status/Home으로 돌아가지 않는다.

---

# 38. Trophy 버튼

권장:

```text
HOLD OK -> STATUS
```

Short press로 즉시 Trophy가 사라지지 않게 한다.

기존 `OK: RECAP`은 제거.

---

# 39. Progress Reset

BLE Admin/reset 시 Trophy state도 완전히 해제.

필수:

```cpp
noTone(Pins::BUZZER);

victory.active = false;
victory.ledSweep = false;
victory.phase = VictoryPhase::Idle;

solvedMask = 0;
saveMask();

updateProgressLeds();

screen = Screen::Status;
drawStatus();
```

reset 후 LED sweep가 남아 있으면 버그.

---

# 40. BLE Admin 상태

Trophy Mode는 UI/LED layer일 뿐 solvedMask를 변경하지 않는다.

BLE status 의미 유지.

`screenName()`에는 `FirewallGame` 추가.

---

# 41. Games는 Challenge에 포함하지 않는다

다시 강조:

```text
FLAPPY HACKER
FIREWALL BREAKER
```

둘 다 아래 계산에 포함하지 않는다.

```cpp
solvedMask
TOTAL_CHALLENGE_COUNT
serialSolvedCount()
allSolved()
```

`TOTAL_CHALLENGE_COUNT == 5` 관련 static_assert 유지.

---

# 42. Flappy 유지

기존:

```text
SCORE 5 = HINT
```

및 Hidden Access hint를 유지한다.

Breakout 추가하면서 Flappy 로직을 불필요하게 수정하지 않는다.

---

# 43. Hidden Access 유지

GPIO condition 자체는 변경하지 않는다.

변경 가능한 부분은 오직:

```text
Hidden Access가 마지막 solved event일 때 Trophy/Victory로 연결
```

부분.

---

# 44. 권장 함수 구성

## Firewall

```cpp
void resetFirewallBricks();
void enterFirewallGame();
void startFirewallGame(uint32_t now);

void drawFirewallIntro();
void drawFirewallRunning();
void drawFirewallOver();
void drawFirewallClear();

void updateFirewallGame(uint32_t now);
```

## Trophy

```cpp
void drawCompleteFrame();
void drawComplete();

void startVictorySequence(uint32_t now);
void enterTrophyModeFromBoot(uint32_t now);

void updateVictory(uint32_t now);
void updateVictoryMelody(uint32_t now);
void updateTrophyLedSweep(uint32_t now);

void stopVictoryMode();
```

## LED

```cpp
void updateProgressLeds();
void setAllStatusLeds(bool on);
```

---

# 45. loop 통합

핵심 서비스는 계속 매 loop 실행.

```cpp
void loop() {
  const uint32_t now = millis();

  pollSerial();
  updateBleAdmin(now);
  updateUi(now);

  // Hidden Access 처리
  ...

  updateVictory(now);
  updateTrophyLedSweep(now);

  delay(1);
}
```

긴 blocking delay 추가 금지.

---

# 46. 테스트 가능한 pure logic

가능하면 collision helper를 `logic.h`로 분리.

예:

```cpp
constexpr bool rectsOverlap(...);
```

기존 host test 구조 활용.

---

# 47. 수동 테스트 — Home

- [ ] Home 메뉴 4개
- [ ] 좌/우 wrap 정상
- [ ] MISSIONS
- [ ] FLAPPY HACKER
- [ ] FIREWALL BREAKER
- [ ] STATUS

---

# 48. 수동 테스트 — FIREWALL BREAKER

- [ ] Intro에서 OK Start
- [ ] LEFT hold 시 계속 이동
- [ ] RIGHT hold 시 계속 이동
- [ ] paddle 화면 밖 이동 금지
- [ ] wall collision
- [ ] paddle collision
- [ ] brick collision
- [ ] brick 24개 clear
- [ ] Game Over
- [ ] Retry
- [ ] Hold OK Exit
- [ ] solvedMask 영향 없음
- [ ] LED 진행도 영향 없음

---

# 49. 수동 테스트 — Serial Mission이 마지막

- [ ] 5/5 transition
- [ ] Trophy OLED 즉시
- [ ] `Congratulations!`
- [ ] `AEGIS{PWN3D!}` large Bold
- [ ] `You solved all problems XD`
- [ ] Serial 한국어 축하 메시지
- [ ] Victory melody
- [ ] non-blocking
- [ ] melody 종료 후 LED sweep

---

# 50. 수동 테스트 — Hidden Access가 마지막

- [ ] Serial 1~4 solved
- [ ] Hidden 해결
- [ ] 5/5
- [ ] Victory 누락 없음
- [ ] Trophy
- [ ] Melody
- [ ] Sweep

---

# 51. 수동 테스트 — Boot Trophy

5/5 상태에서 power cycle:

- [ ] Boot logo
- [ ] solvedMask load
- [ ] Home 대신 Trophy
- [ ] `AEGIS{PWN3D!}`
- [ ] Melody 반복 없음
- [ ] LED sweep
- [ ] BLE/Serial 정상

---

# 52. 수동 테스트 — Reset

5/5 상태에서 reset:

- [ ] solvedMask 0
- [ ] melody stop
- [ ] sweep stop
- [ ] progress LED mode 복귀
- [ ] status/home 정상
- [ ] hidden pin config 정상

---

# 53. Wokwi / Hardware 테스트

확인:

```text
FIREWALL paddle speed
ball speed
brick hit
font overflow
AEGIS{PWN3D!} width
button long press
LED sweep speed
buzzer melody
```

실물에서 필요하면 숫자만 튜닝.

---

# 54. Flash/RAM

큰 U8g2 폰트 추가 시 Flash 사용량 확인.

한글/full Unicode font 추가 금지.

ASCII/Latin font만 사용.

---

# 55. README

`firmware/README.md`에 다음 추가:

```text
- FIREWALL BREAKER bonus minigame
- All 5 challenges solved -> Trophy Mode
- Trophy OLED: AEGIS{PWN3D!}
- Last solve -> victory fanfare
- Boot completed badge -> Trophy restore
- Completed badge -> status LED sweep
```

---

# 56. 하지 말아야 할 변경

- Serial 문제 4개 구조 변경 금지
- Mission FLAG/동적 인증 로직 임의 변경 금지
- Hidden Access GPIO condition 변경 금지
- Flappy Hidden hint 삭제 금지
- TOTAL_CHALLENGE_COUNT 변경 금지
- STATUS LED 개수 변경 금지
- BLE Admin 인증 변경 금지
- player-console transport 변경 금지
- Serial baud 변경 금지
- OLED 한글 폰트 추가 금지
- Breakout을 Mission으로 추가 금지
- Breakout clear를 solvedMask에 기록 금지
- 긴 delay 기반 melody/animation 금지

---

# 57. Definition of Done

## FIREWALL BREAKER

- [ ] Home에 추가
- [ ] Intro/Running/Over/Clear
- [ ] LEFT/RIGHT paddle
- [ ] HOLD OK exit
- [ ] wall/paddle/brick collision
- [ ] 24 brick clear
- [ ] Retry
- [ ] bonus game
- [ ] Flappy 정상 유지

## Trophy Mode

- [ ] 5/5 transition 감지
- [ ] Serial-last case 정상
- [ ] Hidden-last case 정상
- [ ] Top `Congratulations!`
- [ ] Center `AEGIS{PWN3D!}` large Bold
- [ ] Bottom `You solved all problems XD`
- [ ] last solve victory melody
- [ ] melody non-blocking
- [ ] event 종료 후 5 LED 왕복
- [ ] LED animation non-blocking
- [ ] reboot 5/5 -> Trophy
- [ ] reboot 시 melody 반복 없음
- [ ] reboot 후 sweep
- [ ] reset 시 Trophy/melody/sweep 종료
- [ ] BLE/Serial 정상
- [ ] Hidden/Flappy 정상

---

# 58. Codex 구현 순서

## Phase 1
Home menu / Screen enum / screenName

## Phase 2
FirewallState / Breakout physics / UI

## Phase 3
Complete 화면 -> Trophy UI

## Phase 4
allSolved transition 중앙화

## Phase 5
non-blocking Victory melody + LED event

## Phase 6
Trophy LED sweep

## Phase 7
Boot allSolved restore / Reset cleanup

## Phase 8
Tests / Wokwi / README

---

# 59. 최종 의도

완료된 배지는 단순히 5/5를 표시하는 장치가 아니라 **Trophy**가 되어야 한다.

```text
Congratulations!

AEGIS{PWN3D!}

You solved all problems XD
```

를 보여주고, 전원을 다시 켜도 완료 상태를 기억하며, 5개 LED가 좌우로 왕복한다.

`FIREWALL BREAKER`는 메인 Challenge 흐름을 건드리지 않는 보너스 게임으로 동작하며, 기존 `FLAPPY HACKER`와 함께 배지를 실제로 가지고 놀 수 있는 장치로 완성한다.

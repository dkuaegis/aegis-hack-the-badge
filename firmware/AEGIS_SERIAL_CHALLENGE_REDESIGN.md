# AEGIS Hack The Badge — Serial Challenge Redesign & Codex Implementation Spec

> Repository: `dkuaegis/aegis-hack-the-badge`  
> Target: ESP32-S3 badge firmware + Web Serial player console  
> Player console deployment target: `https://badge.dkuaegis.org`  
> Document purpose: Codex가 이 문서를 읽고 기존 정적 FLAG 입력형 문제를 인터랙티브/동적 시리얼 문제로 개편할 수 있도록 구현 요구사항을 정의한다.

---

## 1. 목표

현재 펌웨어의 1~4번 문제는 `Problem.answer`와 사용자의 입력 문자열을 직접 비교하는 정적 구조다.

현재 핵심 흐름은 대략 다음과 같다.

```text
문제 선택
  -> activeProblem 설정
  -> serialText 출력
  -> OLED에 oledLines 표시
  -> 사용자 입력
  -> strcmp(input, problems[activeProblem].answer)
  -> 일치하면 solved()
```

이번 개편에서는 ESP32의 런타임 상태를 활용하여 문제를 다음처럼 변경한다.

```text
01 LEAKED TRANSMISSION   [EASY]
02 DEBUG LEFT ON        [EASY]
03 MAINTENANCE          [HARD]
04 LEGACY AUTH          [HARD]
05 HIDDEN ACCESS        [HIDDEN / 기존 유지]
```

핵심 원칙:

1. **Serial/Web Console에 출력되는 문제 설명과 상호작용 메시지는 한국어로 작성한다.**
2. **OLED에 출력되는 문구는 영어 ASCII만 사용한다.**
3. 1~3번은 비전공자도 접근 가능하거나 명령 탐색으로 해결할 수 있도록 한다.
4. 4번은 ESP32에서 매번 새로운 challenge를 생성하는 **동적 문제**로 만든다.
5. 기존 Hidden Access 문제와 Flappy Hacker 미니게임은 유지한다.
6. 기존 5개 STATUS LED 구조를 유지한다.
7. 플레이어는 별도 `screen`, `minicom`, PuTTY 등을 사용하지 않고 `https://badge.dkuaegis.org`의 Web Serial 콘솔만 사용해도 1~4번을 풀 수 있어야 한다.
8. 기존 BLE 관리자 기능, NVS 문제 편집, 진행도 초기화 기능을 가능한 한 보존한다.

---

# 2. 현재 코드에서 반드시 이해해야 할 구조

## 2.1 `firmware/src/problems.h`

현재 `Problem` 구조체:

```cpp
struct Problem {
  uint8_t version;
  char type; // F: FLAG, C: multiple choice
  uint8_t optionCount;
  char title[PROBLEM_TITLE_SIZE];
  char answer[PROBLEM_ANSWER_SIZE];
  char serialText[PROBLEM_TEXT_SIZE];
  char oledLines[PROBLEM_OPTION_MAX][PROBLEM_OPTION_SIZE];
};
```

현재 문제는 `answer`를 정답 문자열로 사용하며, 1~4번 모두 기본적으로 정적 문자열 비교로 해결된다.

이번 개편에서도 **이 구조체는 가능한 한 유지한다.**

### `answer` 필드의 새로운 의미

| Mission | `answer`의 의미 |
|---|---|
| 01 | 실제 FLAG. 런타임에 HEX 문자열로 변환하여 노출하고, 사용자가 FLAG를 입력하면 해결 |
| 02 | 실제 FLAG. `log` 명령 실행 시 로그에 삽입하여 노출하고, FLAG 입력 시 해결 |
| 03 | 실제 FLAG. 숨겨진 `diag` 명령 진입 성공 시 노출하고, FLAG 입력 시 해결 |
| 04 | 인증 성공 후 출력할 보상 FLAG. **정답 비교에는 사용하지 않음** |
| Hidden | 해당 없음 |

즉 `Problem.answer`를 없애지 않는다.

---

## 2.2 현재 `handleSerialLine()`의 가장 큰 제약

현재 코드에서는 `activeProblem >= 0`인 경우 대략 다음만 처리한다.

```cpp
if (activeProblem >= 0) {
  if (input == "exit") ...
  else if (input == "hint") ...
  else if (input == problems[activeProblem].answer) solved(...)
  else incorrect...
  return;
}
```

이 구조에서는 문제 내부에서 아래와 같은 명령을 사용할 수 없다.

```text
help
info
log
diag
dump
auth
```

따라서 이번 개편의 핵심은 단순히 `DEFAULT_PROBLEMS`를 변경하는 것이 아니라,

> **activeProblem 내부 입력을 문제별 command handler로 dispatch하도록 구조를 변경하는 것**

이다.

---

## 2.3 OLED 제약

현재 코드의 `validProblem()`은 다음 필드를 ASCII로 제한한다.

- `title`
- `oledLines[]`

반면 `serialText`는 ASCII 전용 검사를 하지 않는다.

이 동작은 이번 요구사항과 정확히 일치하므로 유지한다.

### 언어 규칙

```text
title       -> 영어 ASCII
oledLines   -> 영어 ASCII
serialText  -> 한국어 UTF-8 가능
Serial 출력 -> 한국어 UTF-8
```

OLED에 한글 폰트를 추가하지 않는다.

---

## 2.4 Web Serial Player Console

현재 `player-console/app.js`는 다음 설정으로 Web Serial 포트를 연다.

```text
115200 baud
8 data bits
1 stop bit
no parity
no flow control
```

이 설정은 유지한다.

이번 문제들은 모두 **텍스트 기반 명령/응답**으로 설계하므로 Web Console의 `TextEncoder/TextDecoder` 구조를 변경할 필요가 없다.

Binary UART protocol 문제로 변경하지 않는다.

---

# 3. 최종 문제 구성

---

# Mission 01 — LEAKED TRANSMISSION

## 난이도

**하 / 보안에 관심 있는 비전공자 대상**

코딩 지식이 없어도 `hex to text` 검색 또는 CyberChef 같은 도구를 사용하면 풀 수 있어야 한다.

## 학습 포인트

- 컴퓨터의 문자열도 결국 바이트로 표현된다는 사실
- HEX와 ASCII의 관계
- 통신 데이터에서 평문이 노출될 수 있다는 개념

## Serial 문제 설명

문제 진입 시:

```text
[MISSION 01 // LEAKED TRANSMISSION]

장치의 통신 기록에서 정체를 알 수 없는 데이터가 발견되었습니다.

아래 데이터에는 사람이 읽을 수 있는 메시지가 포함되어 있습니다.
원래 메시지를 복원하여 FLAG를 제출하세요.

[CAPTURED DATA]

41 65 67 69 73 7B ...

힌트: 컴퓨터는 문자를 숫자로 표현할 수 있습니다.

FLAG 또는 exit를 입력하세요.
```

### 중요

`[CAPTURED DATA]`의 HEX 문자열을 하드코딩하지 않는다.

반드시 런타임에:

```cpp
problems[MISSION_LEAKED].answer
```

를 byte 단위 uppercase HEX로 변환해서 출력한다.

예를 들어:

```text
Aegis{S3r14l_L34k}
```

이면 HEX 데이터는 자동 생성되어야 한다.

이렇게 해야 BLE 관리자 대시보드에서 FLAG를 수정해도 문제 데이터와 정답이 어긋나지 않는다.

## OLED

```text
LEAKED
TRANSMISSION

HEX -> TEXT
```

가능하면 현재 4-line `oledLines` 구조를 사용한다.

예:

```cpp
{
  "LEAKED",
  "TRANSMISSION",
  "",
  "HEX -> TEXT"
}
```

## 해결 조건

사용자가 복원한 FLAG를 그대로 입력:

```text
Aegis{...}
```

`problems[0].answer`와 일치하면 기존 `solved(0)` 호출.

즉 Mission 01은 최종 제출만큼은 기존 정적 FLAG 비교 방식을 사용해도 된다.

---

# Mission 02 — DEBUG LEFT ON

## 난이도

**하 / 보안에 관심 있는 비전공자 대상**

명령어를 직접 탐색해 보는 경험을 주되, 프로그래밍을 요구하지 않는다.

## 학습 포인트

- `help`를 통한 인터페이스 탐색
- 디버그 기능이 운영 환경에 남아 있을 때의 위험성
- 로그에 민감정보를 기록하면 안 되는 이유

## Serial 문제 설명

```text
[MISSION 02 // DEBUG LEFT ON]

운영용으로 배포된 장치에서 디버그 기능이 활성화되어 있다는 제보가 있습니다.

시리얼 콘솔을 조사하여 장치 내부에서 노출된 FLAG를 찾아보세요.

어떤 명령어를 사용할 수 있는지 확인하는 것부터 시작해보세요.
```

## OLED

```text
DEBUG
LEFT ON

EXPLORE
THE CONSOLE
```

## 문제 내부 지원 명령어

Mission 02가 active 상태일 때:

```text
help
info
log
hint
exit
<FLAG>
```

를 처리한다.

### `help`

```text
사용 가능한 명령어:

  help    도움말
  info    장치 정보 확인
  log     시스템 로그 확인
  hint    OLED 힌트 다시 표시
  exit    문제 종료
```

### `info`

```text
[DEVICE INFORMATION]

장치명      : AEGIS BADGE Rev.3
펌웨어      : 3.x
동작 모드   : PLAYER
디버그 모드 : ENABLED

경고: 운영 환경에서 디버그 기능이 활성화되어 있습니다.
```

OLED를 일시적으로 다음 내용으로 갱신해도 된다.

```text
DEBUG MODE

ENABLED
```

단, OLED 갱신은 필수는 아니며 기존 문제 힌트 화면을 유지해도 된다.

### `log`

```text
[SYSTEM LOG]

10:31:02 시스템 부팅 완료
10:31:02 OLED 초기화 완료
10:31:03 Serial Console 시작
10:31:03 사용자 문제 데이터 로드
10:31:03 DEBUG: recovery_token=Aegis{...}
```

여기서 FLAG는 절대 하드코딩하지 말고:

```cpp
problems[MISSION_DEBUG].answer
```

를 출력한다.

### 해결 조건

사용자가 로그에서 발견한 FLAG를 입력하면:

```cpp
strcmp(input, problems[MISSION_DEBUG].answer) == 0
```

일 때 `solved(MISSION_DEBUG)`.

### 잘못된 명령

```text
알 수 없는 명령입니다. help를 입력해 사용할 수 있는 명령어를 확인하세요.
```

와 같이 안내한다.

Mission 02에서는 사용자가 막히지 않게 해야 한다.

---

# Mission 03 — MAINTENANCE

## 난이도

**상**

Mission 02에서 배운 콘솔 탐색 경험을 확장한다.

## 학습 포인트

- 일반 도움말에 없는 숨겨진 기능
- 운영 빌드에 개발/진단 인터페이스가 남아 있는 위험성
- 정보 수집 후 숨겨진 command를 추론하는 과정

## Serial 문제 설명

```text
[MISSION 03 // MAINTENANCE]

개발 과정에서 사용하던 유지보수 기능이
운영 펌웨어에도 포함되어 있다는 정황이 발견되었습니다.

일반 도움말에는 해당 기능이 표시되지 않습니다.

숨겨진 유지보수 인터페이스를 찾아 FLAG를 획득하세요.
```

## OLED

```text
MAINTENANCE

INTERFACE
HIDDEN
```

## Mission 03 명령

```text
help
info
diag   <- hidden command, help에는 표시하지 않음
hint
exit
<FLAG>
```

## `help`

일부러 `diag`를 표시하지 않는다.

```text
사용 가능한 명령어:

  help    도움말
  info    장치 정보 확인
  hint    OLED 힌트 다시 표시
  exit    문제 종료
```

## `info`

```text
[DEVICE INFORMATION]

장치명 : AEGIS BADGE Rev.3
빌드   : rev3-prod

로드된 모듈:
 - display
 - storage
 - serial
 - diag
```

이 출력으로 사용자가 `diag`라는 명령을 추론할 수 있어야 한다.

무작위 brute force가 필수가 되어서는 안 된다.

## `diag`

사용자가 다음을 입력:

```text
diag
```

하면:

```text
[DIAGNOSTIC INTERFACE]

유지보수 인터페이스에 접근했습니다.

운영 펌웨어에서 관리자용 진단 기능이 노출되어 있습니다.

FLAG:
Aegis{...}

FLAG를 제출하거나 exit를 입력하세요.
```

FLAG는:

```cpp
problems[MISSION_MAINTENANCE].answer
```

를 사용한다.

OLED:

```text
DIAGNOSTIC
INTERFACE

ACCESS
GRANTED
```

## 해결 조건

사용자가 출력된 FLAG를 입력하면 `solved(MISSION_MAINTENANCE)`.

즉 Mission 03은 `diag` 진입 자체로 자동 해결하지 않는다.

FLAG를 한 번 확인한 뒤 제출하는 기존 UX를 유지한다.

---

# Mission 04 — LEGACY AUTH

## 난이도

**상 / 동적 문제**

이 문제만큼은 기존의:

```cpp
strcmp(input, problems[index].answer)
```

방식으로 해결할 수 없어야 한다.

## 학습 포인트

- Challenge-Response 인증
- 동일한 약한 연산을 반복 사용했을 때 패턴이 노출되는 문제
- XOR
- 정적 비밀번호 대신 런타임 challenge를 분석하는 경험

## Serial 문제 설명

```text
[MISSION 04 // LEGACY AUTH]

유지보수 인터페이스에는 관리자 인증 기능이 존재합니다.

하지만 오래된 인증 방식이 그대로 사용되고 있는 것으로 보입니다.

과거 인증 기록을 분석하여 현재 challenge에 대한 올바른 response를 계산하세요.
```

## OLED

기본:

```text
LEGACY AUTH

ANALYZE
THE PATTERN
```

인증 challenge 생성 후:

```text
AUTH REQUIRED

CHALLENGE
ABCD
```

인증 성공:

```text
AUTH SUCCESS

ACCESS
ELEVATED
```

---

# 4. Mission 04 동적 인증 설계

## 4.1 인증 알고리즘

기본 개념:

```text
response = challenge XOR key
```

16-bit unsigned 정수로 처리한다.

하지만 모든 배지에서 똑같은 key를 쓰는 것보다 ESP32의 장치 정보를 사용해 **배지별 key**를 만드는 것을 권장한다.

예:

```cpp
uint16_t makeLegacyKey() {
  const uint64_t mac = ESP.getEfuseMac();
  return static_cast<uint16_t>((mac & 0xFFFFu) ^ 0x1337u);
}
```

이 값은 사용자에게 직접 출력하지 않는다.

### 이유

- 각 배지마다 challenge-response 결과가 달라진다.
- 다른 참가자의 최종 response를 그대로 복사해서 풀기 어렵다.
- 플레이어는 자신의 배지에서 제공되는 과거 기록을 통해 key를 추론해야 한다.

보안용 인증이 아니라 CTF용 의도적 취약점이므로 강한 암호 알고리즘을 사용하지 않는다.

---

## 4.2 과거 인증 기록

과거 challenge 값은 고정해도 된다.

예:

```cpp
constexpr uint16_t AUTH_HISTORY_CHALLENGES[] = {
  0x1234,
  0xABCD,
  0x7777,
};
```

response는 하드코딩하지 말고 런타임에:

```cpp
legacyAuthResponse(historyChallenge, legacyKey)
```

로 계산한다.

`diag` 진입 후 `log` 또는 `dump authlog` 명령으로 다음 형식의 데이터를 보여준다.

```text
[AUTH HISTORY]

challenge=1234 response=XXXX
challenge=ABCD response=XXXX
challenge=7777 response=XXXX
```

같은 배지에서는 모든 pair에 동일한 XOR key가 적용되어야 한다.

---

## 4.3 현재 challenge

사용자가:

```text
auth
```

를 입력하면 ESP32가 새로운 16-bit challenge를 생성한다.

예:

```cpp
do {
  authChallenge = static_cast<uint16_t>(esp_random() & 0xFFFFu);
} while (authChallenge == 0);
```

출력:

```text
[AUTHENTICATION REQUIRED]

challenge: 5A13

response를 계산한 뒤 다음 형식으로 입력하세요.

auth <response>
```

response 형식:

```text
4자리 hexadecimal
대소문자 허용
0x prefix는 허용하지 않아도 됨
```

예:

```text
auth 4924
```

### 올바른 response

```cpp
expected = legacyAuthResponse(authChallenge, legacyKey)
```

사용자 입력을 parse한 값과 비교한다.

---

## 4.4 challenge lifetime

다음 규칙을 사용한다.

- Mission 04 진입 직후 challenge는 없음.
- `auth` 실행 시 새 challenge 생성.
- `auth <response>`는 현재 challenge가 존재할 때만 검증.
- 틀린 response를 입력해도 현재 challenge는 유지한다.
- `auth`를 다시 입력하면 기존 challenge를 버리고 새 challenge 생성.
- Mission 04에서 완전히 `exit`하면 challenge 무효화.
- progress reset 시 challenge 무효화.
- reboot 시 당연히 런타임 challenge는 사라진다.

challenge는 NVS에 저장하지 않는다.

---

## 4.5 Mission 04 diagnostic shell

Mission 04에서는 다음 순서로 진행한다.

```text
Mission 04
   |
   +-- diag
         |
         +-- help
         +-- dump
         +-- log
         +-- auth
         +-- auth <response>
         +-- exit
```

### `diag`

Mission 03에서 배운 hidden command를 재사용한다.

Mission 04 문제 설명에는 유지보수 인터페이스를 이용해야 한다는 문맥을 제공한다.

### `dump`

```text
[AUTH CONFIGURATION]

인증 방식 : legacy-v1
Device ID : <badge id의 짧은 표현>
```

key는 출력하지 않는다.

### `log`

과거 challenge-response pair 출력.

### `auth`

새 challenge 생성.

### `auth <response>`

성공 시:

```text
인증 성공.

권한이 상승되었습니다.

PLAYER -> OPERATOR

FLAG:
Aegis{...}
```

여기서 FLAG는:

```cpp
problems[MISSION_LEGACY_AUTH].answer
```

를 출력한다.

그리고 즉시:

```cpp
solved(MISSION_LEGACY_AUTH);
```

호출.

### 매우 중요

Mission 04에서는 사용자가 다음을 입력해도 해결되어서는 안 된다.

```text
Aegis{...}
```

즉 `problems[3].answer`를 직접 입력하는 것으로 우회할 수 없어야 한다.

Mission 04의 해결 조건은 반드시 **올바른 동적 response 인증 성공**이다.

---

# 5. 권장 상수 및 문제 인덱스

`0`, `1`, `2`, `3` magic number를 코드 전역에서 직접 사용하지 않는다.

예:

```cpp
constexpr uint8_t MISSION_LEAKED = 0;
constexpr uint8_t MISSION_DEBUG = 1;
constexpr uint8_t MISSION_MAINTENANCE = 2;
constexpr uint8_t MISSION_LEGACY_AUTH = 3;
```

또는:

```cpp
enum class MissionId : uint8_t {
  LeakedTransmission = 0,
  DebugLeftOn = 1,
  Maintenance = 2,
  LegacyAuth = 3,
};
```

기존 API가 `uint8_t` index를 많이 사용하므로 과도한 enum conversion이 필요하면 단순 `constexpr`를 사용해도 된다.

---

# 6. Serial 입력 처리 구조 개편

## 현재 구조

```text
handleSerialLine()
  -> activeProblem?
       -> exit / hint / static answer
       -> return
  -> root shell command
```

## 목표 구조

```text
handleSerialLine()
  |
  +-- trim input
  |
  +-- activeProblem < 0
  |     -> handleRootCommand()
  |
  +-- activeProblem == Mission 01
  |     -> handleLeakedMissionCommand()
  |
  +-- activeProblem == Mission 02
  |     -> handleDebugMissionCommand()
  |
  +-- activeProblem == Mission 03
  |     -> handleMaintenanceMissionCommand()
  |
  +-- activeProblem == Mission 04
        -> handleLegacyAuthMissionCommand()
```

권장 함수:

```cpp
void handleRootSerialCommand(const char *input);
void handleMissionSerialCommand(uint8_t index, const char *input);

void handleLeakedMissionCommand(const char *input);
void handleDebugMissionCommand(const char *input);
void handleMaintenanceMissionCommand(const char *input);
void handleLegacyAuthMissionCommand(const char *input);
```

공통 명령은 helper로 빼도 된다.

예:

```cpp
bool handleCommonMissionCommand(uint8_t index, const char *input);
```

처리 대상:

```text
exit
hint
```

주의: Mission 04의 diagnostic sub-shell에서 `exit`는 먼저 diagnostic shell을 빠져나오는 의미로 사용한다.

즉 `exit` semantics:

```text
Mission 01~03:
  exit -> 문제 종료 -> Home

Mission 04 / normal mission:
  exit -> 문제 종료 -> Home

Mission 04 / diagnostic shell:
  exit -> diagnostic shell 종료 -> Mission 04 상태로 복귀
```

---

# 7. Mission 04 런타임 상태

현재 `activeProblem` 하나만으로는 nested diagnostic shell과 challenge 상태를 표현하기 어렵다.

다음과 같은 최소 상태를 추가한다.

```cpp
enum class PlayerShellMode : uint8_t {
  Mission,
  Diagnostic,
};

PlayerShellMode playerShellMode = PlayerShellMode::Mission;

uint16_t legacyAuthKey = 0;
uint16_t legacyAuthChallenge = 0;
bool legacyAuthChallengeValid = false;
```

또는 구조체 사용:

```cpp
struct ChallengeSession {
  PlayerShellMode shellMode = PlayerShellMode::Mission;
  uint16_t legacyKey = 0;
  uint16_t authChallenge = 0;
  bool authChallengeValid = false;
};

ChallengeSession challengeSession;
```

### 권장

구조체를 사용한다.

향후 문제가 추가될 경우 상태를 확장하기 쉽다.

---

# 8. helper 로직

`firmware/src/logic.h`는 현재 host test 가능한 순수 로직이 들어 있다.

동적 인증 계산도 여기로 이동하는 것을 권장한다.

추가:

```cpp
constexpr uint16_t legacyAuthResponse(uint16_t challenge, uint16_t key) {
  return static_cast<uint16_t>(challenge ^ key);
}
```

HEX parser는 Arduino 의존성 없이 작성 가능하면 역시 순수 helper로 분리한다.

예:

```cpp
bool parseHex16(const char *text, uint16_t &value);
```

요구사항:

- 정확히 4 hex digit
- `0-9`, `a-f`, `A-F` 허용
- trailing junk 거부
- 빈 문자열 거부

출력 formatting은:

```cpp
Serial.printf("%04X", value);
```

사용.

---

# 9. `showProblem()` 개편

현재 `showProblem()`은 모든 문제에 대해 동일하게:

```text
serialText 출력
OLED hint 표시
"FLAG 또는 exit..."
```

를 출력한다.

Mission별 intro가 다르므로 최소한 footer 안내를 분기한다.

권장:

```cpp
void showProblem(uint8_t index) {
  activeProblem = index;
  resetMissionRuntime(index);
  screen = Screen::Hint;
  drawHint(index);

  Serial.println();
  Serial.println(problems[index].serialText);

  switch (index) {
    case MISSION_LEAKED:
      printHexEncodedAnswer(problems[index].answer);
      Serial.println("...");
      break;

    case MISSION_DEBUG:
      Serial.println("help부터 입력해보세요.");
      break;

    case MISSION_MAINTENANCE:
      Serial.println("...");
      break;

    case MISSION_LEGACY_AUTH:
      Serial.println("...");
      break;
  }

  beep(659);
}
```

Mission 01의 HEX payload는 `showProblem()` 진입 시 생성한다.

---

# 10. OLED 화면 처리

기존 `drawHint()`와 `oledLines`를 최대한 활용한다.

### 기본 문제 OLED

각 `DEFAULT_PROBLEMS`의 `oledLines`를 다음처럼 구성한다.

#### Mission 01

```text
LEAKED
TRANSMISSION

HEX -> TEXT
```

#### Mission 02

```text
DEBUG
LEFT ON

EXPLORE
THE CONSOLE
```

#### Mission 03

```text
MAINTENANCE

INTERFACE
HIDDEN
```

#### Mission 04

```text
LEGACY AUTH

ANALYZE
THE PATTERN
```

현재 `PROBLEM_OPTION_MAX == 4`이므로 4줄 범위에 맞춘다.

문구 길이는 기존 `PROBLEM_OPTION_SIZE` 제한을 지켜야 한다.

---

## Mission 04 challenge OLED

Mission 04에서 `auth`가 실행되면 기본 `drawHint()` 대신 전용 화면을 그리는 것이 좋다.

예:

```cpp
void drawLegacyAuthChallenge(uint16_t challenge);
void drawLegacyAuthSuccess();
```

challenge:

```text
AUTH REQUIRED

CHALLENGE
5A13
```

success:

```text
AUTH SUCCESS

ACCESS
ELEVATED
```

ASCII만 사용한다.

---

# 11. `problems.h` 기본 문제 데이터 변경

기존:

```text
The Word
CQ CQ CQ
Decode
King Caesar
```

를 제거하고 새 문제로 교체한다.

예상 기본 데이터:

```cpp
constexpr Problem DEFAULT_PROBLEMS[] = {
  // 01 LEAKED TRANSMISSION
  // 02 DEBUG LEFT ON
  // 03 MAINTENANCE
  // 04 LEGACY AUTH
};
```

## Version bump

기존 장비 NVS에 과거 문제가 저장되어 있으면 `DEFAULT_PROBLEMS`를 바꿔도 이전 NVS 데이터가 우선 로드될 수 있다.

따라서:

```cpp
constexpr uint8_t PROBLEM_STORAGE_VERSION = 2;
```

로 bump하는 것을 권장한다.

현재 `loadProblems()`는 version이 맞지 않는 저장 데이터를 invalid로 보고 default로 되돌리므로, 구조체 크기를 바꾸지 않아도 새 기본 문제를 적용할 수 있다.

### 중요

`Problem` struct layout은 가능하면 변경하지 않는다.

이렇게 하면:

- BLE problem get/set protocol
- admin bridge
- dashboard editor
- NVS bytes size

를 크게 바꾸지 않아도 된다.

---

# 12. 권장 기본 FLAG

개발 기본값 예시:

```text
01 Aegis{S3r14l_L34k}
02 Aegis{D3bug_L0gs_4r3_D4ng3r0us}
03 Aegis{H1dd3n_D14gn0st1c}
04 Aegis{L3g4cy_4uth_1s_N0t_S4f3}
```

행사 전 관리자 대시보드 또는 펌웨어 기본값에서 변경 가능하게 유지한다.

Mission 04의 `answer`는 dynamic response가 아니라 **auth success reward FLAG**임을 주석으로 명확히 남긴다.

---

# 13. BLE 관리자 기능 호환성

현재 BLE 관리자 기능에는:

```text
problem get 1-4
problem set ...
reset
reboot
status
```

가 있으며 `Problem.answer`도 전송/수정한다.

이번 개편에서는 `Problem` struct를 유지하므로 기본 프로토콜은 깨지지 않도록 한다.

## 반드시 지켜야 할 것

- `problem get/set` 계속 동작
- 문제 제목 수정 가능
- Serial 한국어 본문 수정 가능
- OLED 영어 문구 수정 가능
- FLAG 수정 가능
- 문제 수정 시 기존처럼 해당 문제 solved bit 초기화
- Hidden Access는 관리자 문제 편집 대상에 포함하지 않음

## Mission 04 특이사항

Mission 04에서 dashboard의 `answer` 필드는:

```text
"정답 문자열"
```

이라기보다:

```text
"인증 성공 시 출력할 FLAG"
```

다.

가능하면 admin dashboard UI label을:

```text
ANSWER / REWARD FLAG
```

또는 한국어:

```text
정답 / 보상 FLAG
```

처럼 변경한다.

필수는 아니지만 혼동 방지를 위해 권장한다.

---

# 14. BLE 관리자 셸의 사용자 문제 실행

현재 BLE 관리자 셸도 1~4번 문제를 선택하고 `bleActiveProblem`에서 정적 answer 비교를 수행한다.

새 동적 문제와 로직이 달라질 경우 Serial과 BLE에서 문제 동작이 달라지는 문제가 생길 수 있다.

## 권장 구현

가능하면 문제 입력 처리 로직을 Serial과 BLE에서 중복 구현하지 않는다.

### Option A — 권장

공통 Challenge Engine을 만들고 출력 transport만 분리한다.

개념:

```cpp
enum class OutputTarget {
  UsbSerial,
  BleAdmin,
};
```

또는 callback:

```cpp
using LineWriter = void (*)(const char *);
```

공통:

```cpp
handlePlayerCommand(context, input, writer);
```

Serial writer:

```cpp
Serial.println(...)
```

BLE writer:

```cpp
bleSendLine(...)
```

### Option B — 최소 수정

플레이어용 동적 문제는 USB Serial에서만 완전히 지원하고,
BLE 관리자 셸에서는 1~4 문제 플레이 기능을 제거하거나 제한한다.

이 경우 관리자 기능은:

```text
status
problem get
problem set
reset
reboot
```

위주로 유지한다.

### 선택

**Option A를 우선 구현한다.**

단, 리팩토링 규모가 과도하게 커져 안정성이 떨어지는 경우 Option B로 전환해도 된다.

어떤 방식을 선택했는지 코드 주석과 README에 기록한다.

---

# 15. Root shell 명령

Root shell은 기존 UX를 크게 바꾸지 않는다.

권장:

```text
aegis
1
2
3
4
status
help
hint
clear
```

`info`, `log`, `diag`는 root에서 전역으로 열지 않는다.

이 명령들은 각 Mission 내부에서만 활성화한다.

이렇게 해야 다른 문제의 FLAG가 의도치 않게 노출되지 않는다.

Root `help` 예시:

```text
사용 가능한 명령어:

  1-4       문제 선택
  status    문제 진행 상태 확인
  help      도움말
  clear     콘솔 화면 정리
  aegis     배지 정보 다시 표시

문제 내부에서는 각 문제에 맞는 명령을 사용할 수 있습니다.
```

---

# 16. `solved()` 처리

기존 `solved(uint8_t index)`의 진행도/NVS/LED/beep/Complete 로직은 유지한다.

각 문제에서 해결 조건을 만족했을 때만 이 함수를 호출한다.

```text
Mission 01 -> FLAG 직접 제출 성공
Mission 02 -> log에서 찾은 FLAG 직접 제출 성공
Mission 03 -> diag에서 찾은 FLAG 직접 제출 성공
Mission 04 -> dynamic auth response 성공
Hidden     -> 기존 GPIO condition
```

---

# 17. Progress Reset 시 런타임 상태 초기화

현재 `resetProgress()`는 solvedMask와 active problem 상태를 초기화한다.

여기에 challenge session도 초기화한다.

예:

```cpp
void resetChallengeSession() {
  challengeSession.shellMode = PlayerShellMode::Mission;
  challengeSession.authChallenge = 0;
  challengeSession.authChallengeValid = false;
}
```

`resetProgress()`에서 호출.

또한:

- Mission 04 exit
- Mission 변경
- 필요한 경우 문제 수정

시에도 challenge 상태를 invalidate한다.

---

# 18. Hidden Access 유지

기존 Hidden Access 로직은 변경하지 않는다.

기존 의도:

```text
C0 -> LOW output
C1 -> open
C2 -> LOW detected
약 1200ms 유지
```

성공 시:

```text
HIDDEN ACCESS
GRANTED
```

화면 표시.

기존:

```cpp
TOTAL_CHALLENGE_COUNT = SERIAL_PROBLEM_COUNT + 1;
```

과:

```cpp
static_assert(TOTAL_CHALLENGE_COUNT == 5, ...)
```

도 유지한다.

즉 Serial Mission 4개 + Hidden 1개의 전체 구조를 유지한다.

---

# 19. Flappy Hacker 유지

기존 미니게임과:

```text
shorting board Front C0-C2
```

보상 힌트는 유지한다.

이번 Serial 문제 개편 때문에 Flappy game physics, collision, score logic을 변경하지 않는다.

---

# 20. Player Web Console 수정

## `player-console/app.js`

Web Serial 설정은 그대로 유지:

```js
const BAUD_RATE = 115200;
```

Binary transport를 추가하지 않는다.

### placeholder

기존:

```text
1-4 | hint | status | help | exit
```

에서 문제 내부 command가 있다는 것을 반영해 조금 더 일반화한다.

권장:

```text
COMMAND OR FLAG
```

또는:

```text
1-4 | help | status | command | FLAG
```

첫 번째가 더 깔끔하다.

## `player-console/index.html`

Quick Start는 다음 수준으로 유지한다.

```text
1. 배지를 USB로 연결합니다.
2. CONNECT USB를 누릅니다.
3. 배지 Serial 포트를 선택합니다.
4. aegis 또는 1~4를 입력합니다.
5. 문제의 안내에 따라 명령 또는 FLAG를 입력합니다.
```

Web Console이 문제 풀이법 자체를 스포일러하지 않도록:

```text
info
log
diag
auth
```

명령을 Quick Start에 직접 적지 않는다.

---

# 21. `badge.dkuaegis.org` 배포 관련

플레이어 콘솔은 Web Serial을 사용하므로 배포 환경은 HTTPS를 유지한다.

브라우저가 실제 USB 장치에 직접 접근한다.

구조:

```text
badge.dkuaegis.org
       |
       | HTTPS로 정적 페이지 제공
       v
Player Browser
       |
       | Web Serial
       v
ESP32-S3 Badge
```

Serial 문제 데이터가 웹 서버를 통해 전달되는 구조로 바꾸지 않는다.

---

# 22. 테스트 추가

현재 `firmware/test/test_logic.cpp`에 순수 로직 테스트가 존재한다.

동적 인증 helper 테스트를 추가한다.

## 최소 테스트

```cpp
assert(legacyAuthResponse(0x1234, 0x1337) == 0x0103);
assert(legacyAuthResponse(0xABCD, 0x1337) == 0xB8FA);
assert(legacyAuthResponse(0x7777, 0x1337) == 0x6440);
```

`parseHex16()`을 별도 순수 함수로 만들었다면:

```text
"0000" -> success
"4924" -> success
"abcd" -> success
"ABCD" -> success
"0x12" -> reject
"123"  -> reject
"12345"-> reject
"12G4" -> reject
""     -> reject
```

테스트.

Hidden Access와 Flappy 기존 테스트는 삭제하지 않는다.

---

# 23. 수동 통합 테스트

## Mission 01

1. `1` 입력
2. Serial 문제 설명이 한국어인지 확인
3. OLED가 영어인지 확인
4. 출력된 HEX가 현재 `problems[0].answer`를 정확히 encode했는지 확인
5. 잘못된 FLAG 입력 -> 실패
6. 올바른 FLAG 입력 -> solved
7. LED 1 켜짐

## Mission 02

1. `2`
2. `help`
3. `info`
4. `log`
5. `log`에 현재 `problems[1].answer`가 출력되는지 확인
6. FLAG 입력
7. solved 및 LED 2

## Mission 03

1. `3`
2. `help`에 `diag`가 없는지 확인
3. `info`에 `diag` module 힌트가 있는지 확인
4. `diag`
5. current `problems[2].answer` 출력 확인
6. FLAG 입력
7. solved 및 LED 3

## Mission 04

1. `4`
2. `diag`
3. `log`
4. 세 개의 challenge-response pair 확인
5. 각 pair의 XOR 결과가 동일한 key인지 확인
6. `auth`
7. 4자리 랜덤 challenge 생성 확인
8. OLED challenge 표시 확인
9. 틀린 `auth XXXX` -> 실패, challenge 유지
10. 올바른 response -> 인증 성공
11. `problems[3].answer` 출력
12. 자동 solved
13. LED 4 켜짐
14. Mission 04의 FLAG를 직접 입력해도 solved되지 않는지 확인

## Hidden Access

기존 hardware test 그대로 수행.

## All Clear

Serial 4개 + Hidden Access 해결 후:

```text
ALL CLEAR
ACCESS ELEVATED
AEGIS{PWNED}
```

기존 Complete 화면이 정상 표시되는지 확인.

---

# 24. 문제 편집 후 동작 테스트

BLE Admin Dashboard에서 각 FLAG를 수정한다.

## Mission 01

FLAG 변경 후 새 HEX payload가 변경된 FLAG 기준으로 생성되어야 한다.

## Mission 02

`log`의 `recovery_token=` 값이 변경된 FLAG여야 한다.

## Mission 03

`diag`에서 변경된 FLAG가 출력되어야 한다.

## Mission 04

dynamic response algorithm은 그대로 유지하되 인증 성공 후 변경된 FLAG를 출력해야 한다.

이 테스트를 통해 런타임 로직에 FLAG가 중복 하드코딩되지 않았음을 검증한다.

---

# 25. README 갱신

최소 다음 문서를 수정한다.

```text
firmware/README.md
player-console/README.md
admin/README.md
```

기록할 내용:

- Serial Mission이 정적 answer-only 방식에서 interactive 방식으로 변경됨
- Serial 출력 언어: Korean
- OLED: English ASCII
- Mission 04는 dynamic challenge-response
- Hidden Access 유지
- Web player console 사용 방법
- Admin problem answer 필드의 Mission 04 의미
- `PROBLEM_STORAGE_VERSION` bump 여부

---

# 26. 구현 우선순위

Codex는 다음 순서로 작업한다.

## Phase 1 — 문제 데이터 교체

- `DEFAULT_PROBLEMS` 교체
- `PROBLEM_STORAGE_VERSION` bump
- 제목/OLED 문구 길이 validation 통과 확인

## Phase 2 — Serial challenge dispatcher

- 기존 activeProblem static compare 구조 제거/분기
- Mission별 handler 생성
- common `exit`, `hint` 처리 정리

## Phase 3 — Mission 01~03

- HEX runtime generation
- Mission 02 help/info/log
- Mission 03 hidden diag
- static FLAG submission

## Phase 4 — Mission 04

- ChallengeSession
- device-specific legacy key
- auth history
- random challenge
- hex parse
- dynamic validation
- dedicated OLED screens

## Phase 5 — BLE compatibility

- 관리자 problem get/set 유지
- 가능하면 common challenge engine으로 Serial/BLE 중복 제거
- 불가능하면 BLE 문제 플레이 기능 제한 및 문서화

## Phase 6 — Player Console

- placeholder/Quick Start 수정
- Web Serial transport는 변경하지 않음

## Phase 7 — Tests / Docs

- logic unit test
- manual integration test
- README 업데이트

---

# 27. 구현 시 하지 말아야 할 것

Codex는 다음 변경을 하지 않는다.

- Hidden Access GPIO 조건 변경 금지
- C0-C2 힌트 제거 금지
- Flappy Hacker 삭제/대규모 개편 금지
- STATUS LED 개수 변경 금지
- Serial baud rate 변경 금지
- Web Serial을 binary protocol로 변경 금지
- OLED에 한글 폰트 추가 금지
- BLE 관리자 인증 HMAC 로직을 이번 작업과 섞어 변경하지 말 것
- `Problem` struct를 이유 없이 대규모 변경하지 말 것
- Mission 04 FLAG 문자열 자체를 dynamic auth expected response로 사용하지 말 것
- Mission 04에서 FLAG 직접 입력만으로 solved 처리하지 말 것
- FLAG를 runtime handler 내부에 중복 하드코딩하지 말 것

---

# 28. 보안/운영 주의사항

이 프로젝트의 문제는 교육/행사용 intentionally vulnerable challenge다.

하지만 실제 운영용 관리자 인터페이스와 문제용 의도적 취약점을 섞지 않는다.

특히:

- Mission 03의 `diag`는 **플레이어 Serial challenge 내부 가상 명령**이어야 한다.
- BLE Admin의 실제 HMAC 인증 우회 기능으로 구현하지 않는다.
- Mission 04의 legacy auth는 문제용 로컬 state machine일 뿐 실제 BLE Admin 인증과 연결하지 않는다.
- 실제 `BADGE_ADMIN_KEY`를 문제 데이터나 Serial 로그에 노출하지 않는다.
- 실제 관리자 API/키/nonce를 Mission 04의 예제로 재사용하지 않는다.

즉:

```text
CTF LEGACY AUTH != REAL BLE ADMIN AUTH
```

를 명확히 유지한다.

---

# 29. 공개 소스 주의

행사 중 이 repository가 public이고 참가자가 repository 위치를 알고 있다면 펌웨어 소스에서:

- 기본 FLAG
- 문제 흐름
- `diag` command
- legacy auth 구현

을 직접 확인할 수 있다.

이것이 의도된 풀이 경로가 아니라면 행사 운영 시 다음 중 하나를 고려한다.

1. 행사 펌웨어용 private branch/repository 사용
2. 기본 FLAG를 행사 전 BLE Admin으로 변경
3. Mission 04 key를 device-specific runtime value로 생성
4. 행사 종료 후 source 공개

최소한 Mission 04를 device-specific key로 구현하면 다른 배지의 인증 response 복사는 방지할 수 있다.

---

# 30. 완료 조건 / Definition of Done

다음 조건을 모두 만족해야 작업 완료로 본다.

- [ ] Serial Mission은 정확히 4개다.
- [ ] Hidden Access 포함 전체 challenge는 5개다.
- [ ] 기존 5개 STATUS LED mapping이 유지된다.
- [ ] Serial 문제 설명 및 사용자 안내가 한국어다.
- [ ] OLED 문구는 영어 ASCII다.
- [ ] Mission 01 HEX payload가 현재 answer에서 런타임 생성된다.
- [ ] Mission 02에서 `help -> info/log` 탐색이 정상 동작한다.
- [ ] Mission 02 log FLAG가 current answer를 사용한다.
- [ ] Mission 03 `help`에는 `diag`가 노출되지 않는다.
- [ ] Mission 03 `info`에서 `diag`를 추론할 힌트를 얻을 수 있다.
- [ ] Mission 03 `diag`가 current answer FLAG를 노출한다.
- [ ] Mission 04 challenge가 매 인증 시 런타임 생성된다.
- [ ] Mission 04 response는 challenge-response 계산으로만 검증된다.
- [ ] Mission 04 FLAG 직접 입력으로 우회할 수 없다.
- [ ] Mission 04 성공 시 current `answer` FLAG를 보상으로 출력한다.
- [ ] Mission 04 challenge가 OLED에 영어로 표시된다.
- [ ] progress reset 시 challenge session도 초기화된다.
- [ ] BLE Admin의 problem get/set/reset/reboot/status가 깨지지 않는다.
- [ ] 관리자에서 FLAG 수정 시 Mission 01~04 출력에 변경값이 반영된다.
- [ ] Web Serial 115200/8N1 연결이 그대로 동작한다.
- [ ] Hidden Access가 기존 C0-C2 조건으로 정상 해결된다.
- [ ] Flappy Hacker가 기존처럼 동작한다.
- [ ] 모든 문제 해결 후 Complete 화면이 정상 표시된다.
- [ ] 기존 unit tests가 통과한다.
- [ ] legacy auth helper tests가 추가되고 통과한다.
- [ ] 관련 README가 갱신된다.

---

# 31. Codex 작업 지시 요약

Codex는 이 문서를 구현 명세로 사용한다.

가장 중요한 구조적 변경은 다음 세 가지다.

```text
1. static answer-only handler
   ->
   mission-specific command dispatcher

2. hard-coded challenge content
   ->
   Problem.answer 기반 runtime content generation

3. Mission 04 static answer
   ->
   ESP32 runtime challenge-response state machine
```

최대한 기존 하드웨어/UI/BLE 관리자 구조를 보존하면서 구현한다.

특히 `main.cpp` 한 파일에 모든 코드를 계속 몰아넣기보다, 인증 계산이나 parser처럼 테스트 가능한 로직은 `logic.h` 또는 별도 challenge helper 파일로 분리하는 것을 권장한다.

단, 과도한 아키텍처 리팩토링보다 행사 전에 안정적으로 동작하는 것이 우선이다.

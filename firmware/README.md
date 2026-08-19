# Hack The Badge Rev.3 Firmware

ESP32-S3-WROOM-1-N8R8용 펌웨어입니다. 기존
[`Z3r0c0k3/hacking-box`](https://github.com/Z3r0c0k3/hacking-box) 최신
`main` 커밋 `4b0b2cd`의 Serial 문제 흐름과 영구 상태 저장 방식을 Rev.3 PCB에
맞게 다시 구현했습니다.

## 구현 기능

- USB CDC Serial(115200): 문제 설명, FLAG 제출, 상태 확인
- 128x64 OLED: Cyber/Terminal/Badge UI, 문제 보기/예시, Flappy Hacker 미니게임
- LED1-LED5: 4개 Serial 문제와 `Hidden Access` 풀이 상태
- NVS: 전원을 꺼도 풀이 상태 유지
- `Hidden Access`: 전면 challenge pad의 올바른 두 접점을 1.2초간 쇼트하면 해금
- BLE 관리자: Windows/macOS/Linux PC와 P2P 연결해 장비별 상태, reset, reboot, 무선 관리자 셸 제공

배지는 `AEGIS-XXXXXX` 이름으로 항상 BLE advertising하며 USB와 BLE 입력 상태는
서로 분리됩니다. BLE 관리자 셸에서는 USB 사용자 명령과 관리자 명령을 모두
사용할 수 있습니다. PC용 Python 브리지와 대시보드 실행법은
[`../admin/README.md`](../admin/README.md)를 참고하세요.

운영자 확인용 기본 Hidden Access 조합은 **C1을 개방한 상태에서 C0-C2를
1.2초간 연결**하는 것입니다. 조합이나 유지 시간은 `logic.h`와 `main.cpp`의
`HIDDEN_HOLD_MS`에서 변경할 수 있습니다.

## 빌드와 업로드

PlatformIO에서 다음을 실행합니다.

```bash
cd firmware
pio run
pio run -t upload
pio device monitor
```

보드는 ESP32-S3 DevKitC 프로필, 8 MB flash, 8 MB octal PSRAM 설정을
사용합니다. USB CDC가 보이지 않으면 BOOT를 누른 채 리셋해 처음 한 번
업로드한 뒤 다시 연결하세요.

## 문제 교체

[`src/problems.h`](src/problems.h)의 `DEFAULT_PROBLEMS` 배열은 NVS에 저장된 문제가
없을 때 사용하는 기본값입니다. 실행 중에는 관리자 대시보드의 `EDIT PROBLEMS`로
1~4번을 수정할 수 있습니다. 저장 시 해당 문제의 풀이 상태만 초기화되며
`Hidden Access`는 수정할 수 없습니다.

- `title`: OLED와 상태표에 표시할 짧은 ASCII 제목
- `type`: `F`(FLAG) 또는 `C`(2~4지선다)
- `answer`: FLAG 문자열 또는 선택형 정답 번호
- `serialText`: Serial에 출력할 문제 설명
- `oledLines`: OLED에만 출력할 ASCII 보기/예시 최대 4줄(23바이트 이하)

Rev.3 상태 LED가 5개이므로 기본 구성은 Serial 문제 4개 + Hidden Access 1개입니다.
문제 개수를 바꾸려면 LED 정책과 `static_assert`도 함께 검토해야 합니다.

Hidden Access 힌트는 Flappy Hacker에서 5점을 달성했을 때만 OLED에 표시됩니다.
문구는 같은 파일의 `MINIGAME_REWARD_LINE_1`, 기준 점수는 `main.cpp`의
`FLAPPY_REWARD_SCORE`에서 변경할 수 있습니다.

OLED 화면 흐름은 `Boot → Home → Missions → Intel → Status`이며, 사용자 화면의
진행도와 상태에는 1~4번 Serial 문제만 표시합니다. Home에서
`LEFT/RIGHT`로 메뉴를 고르고 `OK`로 진입합니다. Intel과 Status는 `OK`를
길게 눌러 Home으로 돌아갑니다.

## Serial 명령

| 명령 | 기능 |
| --- | --- |
| `1`~`4` | 문제 선택 |
| `hint` | 선택한 문제의 OLED 보기 다시 표시 |
| `exit` | 문제 풀이 모드 종료 |
| `status` | 전체 풀이 상태 |
| `help` | 사용법 |
| `reset` | 풀이 상태 초기화 |
| `aegis` | 시작 배너 다시 표시 |

## BLE 관리자 셸

BLE 관리 채널은 연결마다 새 challenge를 만들고 fleet key 기반 HMAC 인증 후
명령을 처리합니다. 기본 개발 키는 실제 행사 전에 반드시 교체하세요.

| 명령 | 기능 |
| --- | --- |
| `help` | 관리자 명령 목록 |
| `status` | 장비 ID와 문제 풀이 상태 JSON |
| `reset` | 전체 풀이 상태 초기화 |
| `reboot` | 재부팅 |
| `1`~`4`, `hint`, `exit`, `clear`, `aegis` | USB 사용자 셸과 동일 |
| `problem get 1`~`4` | 대시보드가 사용하는 문제 조회 명령 |

## 안전 및 핀 매핑

핀은 [`src/pins.h`](src/pins.h)에 있으며 PCB 회로 문서와 동일합니다. Hidden
Access 감지 중 C0는 LOW로만 구동되고 C1/C2는 pull-up 입력입니다. 펌웨어의
의도된 쇼트 대상은 보호 저항 뒤의 challenge pad뿐입니다. `3V3`, `VBUS`,
`EN`, `BOOT` 또는 GND를 임의로 쇼트하지 마세요.

OLED는 전체 1 KB framebuffer 대신 U8g2 128바이트 page buffer를 사용하고,
Flappy Hacker도 단일 파이프만 갱신합니다. Serial 입력은 고정 192바이트
버퍼를 사용해 동적 메모리 사용을 줄였습니다.

## 빠른 로직 검사

PlatformIO 없이도 상태 비트와 Hidden Access 판정 로직을 검사할 수 있습니다.

```bash
clang++ -std=c++17 -Ifirmware/src firmware/test/test_logic.cpp -o /tmp/badge-logic-test
/tmp/badge-logic-test
```

## Wokwi 통합 시뮬레이션

VS Code에서 `firmware` 폴더를 열고 PlatformIO로 한 번 빌드한 다음,
Command Palette의 `Wokwi: Start Simulator`를 실행합니다.

```bash
pio run
```

`diagram.json`은 Rev.3의 펌웨어 관찰 가능 회로를 다음과 같이 재현합니다.

- SSD1315와 명령어 호환되는 `board-ssd1306` OLED: GPIO4/5, I2C `0x3c`
- Left/OK/Right active-low 버튼: GPIO9/10/12, 키보드 ←/Space/→
- active-high 상태 LED 5개: GPIO13-17, 실회로와 같은 1k 직렬 저항
- 부저 드라이버 등가 출력: GPIO18
- C0-C1/C0-C2 challenge pad 쇼트 스위치

Hidden Access는 `H`를 1.2초 이상 눌러 C0-C2 쇼트를 재현하면 됩니다.
`J`는 C0-C1 오답 조합입니다. 관리자 부팅은 Left와 Right 버튼을
Cmd-click해 둘 다 고정한 뒤 ESP32-S3 보드의 RST 버튼을 누릅니다.
실물에서는 C0를 LOW로 구동하고 challenge pad의 직렬 저항을 거쳐 C1/C2를
감지합니다. Wokwi에서는 같은 펀웨어 입력 결과를 얻도록 테스트 버튼이
해당 C1/C2 입력을 직접 LOW로 만드는 등가 회로로 구성됩니다.

Wokwi는 GPIO, I2C, 버튼, LED, 부저, USB CDC 편의 동작을 검사하며,
USB-C 전기 특성, 3.3V 전원, ESD, MOSFET 부하, RF와 실제 OLED 편차는
실물 보드에서 별도로 검사해야 합니다.

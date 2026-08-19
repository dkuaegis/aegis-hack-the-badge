# Hack The Badge Rev.3 Firmware

ESP32-S3-WROOM-1-N8R8용 펌웨어입니다. 기존
[`Z3r0c0k3/hacking-box`](https://github.com/Z3r0c0k3/hacking-box) 최신
`main` 커밋 `4b0b2cd`의 Serial 문제 흐름과 영구 상태 저장 방식을 Rev.3 PCB에
맞게 다시 구현했습니다.

## 펌웨어 사양

| 항목 | 설정 |
| --- | --- |
| 대상 보드 | Hack The Badge Rev.3 / ESP32-S3-WROOM-1-N8R8 |
| PlatformIO 환경 | `esp32-s3-rev3` |
| Framework | Arduino for ESP32 |
| Flash / PSRAM | 8 MB QIO flash / 8 MB octal PSRAM |
| USB | ESP32-S3 native USB CDC, `115200 baud` |
| 디스플레이 | 128x64 I2C OLED, SDA GPIO4 / SCL GPIO5 |
| 관리자 통신 | BLE GATT P2P, `AEGIS-XXXXXX` advertising |
| 영구 저장 | ESP32 NVS (`Preferences`) |

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

## 소스 구성

| 파일 | 역할 |
| --- | --- |
| [`platformio.ini`](platformio.ini) | 보드, flash/PSRAM, USB CDC, 라이브러리 설정 |
| [`src/main.cpp`](src/main.cpp) | OLED UI, 버튼·LED·부저, USB/BLE 셸, NVS, Hidden Access |
| [`src/problems.h`](src/problems.h) | 1~4번 기본 문제, 필드 크기와 미니게임 보상 문구 |
| [`src/pins.h`](src/pins.h) | Rev.3 PCB GPIO 매핑 |
| [`src/logic.h`](src/logic.h) | 풀이 비트와 challenge pad 판정 로직 |
| [`test/test_logic.cpp`](test/test_logic.cpp) | 하드웨어 없이 실행하는 핵심 로직 검사 |

## 업로드 준비

필요한 것은 데이터 통신이 가능한 USB-C 케이블과 PlatformIO입니다. 다음 중
한 가지 방식으로 준비합니다.

- VS Code를 사용하면 PlatformIO IDE 확장을 설치하고 `firmware` 폴더를
  프로젝트로 엽니다. 확장에 PlatformIO Core가 포함되므로 별도 설치가
  필요하지 않습니다.
- CLI를 사용하면 PlatformIO 공식
  [Installer Script](https://docs.platformio.org/en/latest/core/installation/methods/installer-script.html)를
  권장합니다. Python 패키지 방식이 필요한 환경에서는 macOS/Linux에서
  `python3 -m pip install -U platformio`, Windows에서
  `py -m pip install -U platformio`를 사용할 수 있습니다.

설치 확인:

```bash
pio --version
```

Windows에서 Python을 별도로 설치했다면 설치 과정에서 PATH 추가를
활성화해야 합니다. Linux에서 포트 권한 오류가 발생하면 PlatformIO 공식
[udev rules 안내](https://docs.platformio.org/en/latest/core/installation/udev-rules.html)를
적용합니다.

## 처음 빌드하고 업로드하기

저장소 루트에서 실행합니다.

```bash
cd firmware
pio run
pio device list
pio run -t upload
pio device monitor
```

각 명령의 의미는 다음과 같습니다.

| 명령 | 기능 |
| --- | --- |
| `pio run` | 의존성 설치와 펌웨어 빌드 |
| `pio device list` | 현재 PC의 Serial 장치와 포트 확인 |
| `pio run -t upload` | 빌드 후 USB로 업로드 |
| `pio device monitor` | `115200 baud` USB 사용자 셸 열기 |
| `pio run -t clean` | 이전 빌드 산출물 삭제 |
| `pio run -t erase` | flash 전체 삭제(NVS 포함) |

빌드된 애플리케이션 이미지는
`.pio/build/esp32-s3-rev3/firmware.bin`에 생성됩니다. 최초 설치는
bootloader와 partition table도 함께 기록해야 하므로 `firmware.bin` 하나를
임의 주소에 쓰지 말고 PlatformIO의 `upload` target을 사용하는 것이
안전합니다.

### 업로드 포트 직접 지정

포트 자동 선택이 실패하거나 여러 배지가 연결되어 있으면 대상 포트를
명시합니다.

```bash
# Windows
pio run -t upload --upload-port COM5
pio device monitor --port COM5

# macOS
pio run -t upload --upload-port /dev/cu.usbmodemXXXX
pio device monitor --port /dev/cu.usbmodemXXXX

# Linux
pio run -t upload --upload-port /dev/ttyACM0
pio device monitor --port /dev/ttyACM0
```

실제 포트 이름은 `pio device list` 결과를 사용합니다. Serial monitor나 다른
프로그램이 같은 포트를 열고 있으면 닫은 뒤 업로드합니다.

### BOOT/EN 복구 업로드

USB CDC 포트가 나타나지 않거나 `Connecting...` 단계에서 실패하면 다음
순서로 ESP32-S3 ROM 다운로드 모드에 진입합니다.

1. 배지를 데이터 통신 가능한 USB-C 케이블로 PC에 연결합니다.
2. `BOOT`를 계속 누릅니다.
3. `EN`을 짧게 눌렀다 놓습니다.
4. `BOOT`를 놓습니다.
5. `pio device list`로 새 포트를 확인하고 `pio run -t upload`를 실행합니다.
6. 업로드 완료 후 `EN`을 한 번 누르거나 USB를 다시 연결합니다.

이 동작은 ESP32-S3의 GPIO0을 LOW로 유지한 채 reset하여 ROM serial
bootloader를 시작하는 절차입니다. 보드의 `BOOT`, `EN`은 challenge pad가
아니므로 참가자 문제 요소로 사용하지 마세요.

## 업로드 후 확인

다음 순서로 한 대를 먼저 검증한 뒤 나머지 배지에 업로드하는 것을
권장합니다.

1. OLED에 Boot 화면과 Home 메뉴가 표시되는지 확인합니다.
2. 부팅음과 `LEFT`/`OK`/`RIGHT` 버튼 입력을 확인합니다.
3. `pio device monitor`에서 `aegis`를 입력해 USB 사용자 셸이 응답하는지
   확인합니다.
4. 1~4번 문제에서 Serial 본문과 OLED 보기/예시가 나뉘어 표시되는지
   확인합니다.
5. LED1~LED4가 1~4번 문제, LED5가 Hidden Access 상태를 표시하는지
   확인합니다.
6. 관리자 브리지를 실행해 `AEGIS-XXXXXX` 장치가 ONLINE/AUTHENTICATED로
   표시되고 상태 조회, 문제 편집, reset, reboot가 동작하는지 확인합니다.

관리자 브리지 실행법은 [`../admin/README.md`](../admin/README.md)를
참고하세요. OLED를 아직 납땜하지 않은 보드에도 펌웨어 업로드, USB Serial,
BLE와 LED 검사는 가능합니다. 이 경우 OLED 관련 확인만 건너뜁니다.

## NVS와 초기화 정책

일반적인 `pio run -t upload`는 NVS 영역을 지우지 않습니다. 따라서 다음
항목은 새 펌웨어를 올린 뒤에도 남을 수 있습니다.

- 해결한 문제와 Hidden Access 상태
- 관리자 대시보드에서 편집한 1~4번 문제

풀이 상태만 지우려면 관리자 대시보드의 `RESET SOLVED` 또는 관리자 셸의
`reset`을 사용합니다. `src/problems.h`의 기본 문제로 완전히 되돌리려면
flash 전체를 지운 뒤 다시 업로드합니다.

```bash
cd firmware
pio run -t erase
pio run -t upload
```

`erase`는 문제, 풀이 상태와 펌웨어를 포함한 flash 전체를 삭제하는
파괴적 명령입니다. 반드시 올바른 배지 포트를 확인하고, 실행 직후 펌웨어를
다시 업로드하세요.

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

OLED 화면 흐름은 `Boot → Home → Missions → Intel → Status`입니다.
Hidden Access 성공 전에는 1~4번 Serial 문제만 표시하고, 성공 순간에
`HIDDEN ACCESS / GRANTED`와 성공음을 출력한 뒤 Status에
`HIDDEN ACCESS CLEAR`를 추가합니다. Home에서
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
| `aegis` | 시작 배너 다시 표시 |

## BLE 관리자 셸

BLE 관리 채널은 연결마다 새 challenge를 만들고 fleet key 기반 HMAC 인증 후
명령을 처리합니다. 기본 개발 키는 실제 행사 전에 반드시 교체하세요.

기본 키는 `src/main.cpp`의 `BADGE_ADMIN_KEY`이며
`AEGIS_DEV_ONLY_CHANGE_ME`로 설정되어 있습니다. 행사 전 이 값을 운영용
키로 변경해 모든 배지에 다시 업로드하고, 브리지 실행 환경의
`BADGE_ADMIN_KEY`에도 동일한 값을 설정합니다. 두 값이 다르면 장치는
발견되지만 `AUTHENTICATED` 상태가 되지 않습니다. OS별 설정 예시는
[`../admin/README.md`](../admin/README.md#관리자-키)를 참고하세요.

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

| 기능 | GPIO | 동작 |
| --- | --- | --- |
| OLED SDA / SCL | 4 / 5 | I2C `0x3C`, 400 kHz |
| Challenge C0 / C1 / C2 | 6 / 7 / 8 | C0 LOW 출력, C1/C2 pull-up 입력 |
| LEFT / OK / RIGHT | 9 / 10 / 12 | active-low |
| LED1~LED5 | 13~17 | active-high |
| Passive buzzer | 18 | MOSFET 구동 |
| UART TX / RX | 43 / 44 | 3.3 V UART |

OLED는 전체 1 KB framebuffer 대신 U8g2 128바이트 page buffer를 사용하고,
Flappy Hacker도 단일 파이프만 갱신합니다. Serial 입력은 고정 192바이트
버퍼를 사용해 동적 메모리 사용을 줄였습니다.

## 펌웨어 업로드 보안 범위

현재 펌웨어에는 OTA 업데이트가 없으며 새 펌웨어는 물리 USB 연결로만
업로드합니다. 관리자 대시보드도 펌웨어 업로드나 업로드 잠금 기능을
제공하지 않습니다.

ESP32-S3의 `BOOT`+`EN` 조합은 애플리케이션보다 먼저 ROM download mode로
진입하므로, NVS 값이나 관리자 페이지 토글처럼 되돌릴 수 있는 소프트웨어
설정으로 물리적인 재업로드를 확실히 차단할 수 없습니다. 현재 개발 설정은
Secure Boot와 Flash Encryption을 활성화하지 않았습니다.

행사 장비에서 임의 펌웨어 실행을 방지해야 한다면 별도 양산 절차로
[Secure Boot V2](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/security/secure-boot-v2.html)와
[UART download mode 보안 설정](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/security/security.html)을
검토해야 합니다. eFuse 설정은 되돌릴 수 없으며 잘못 적용하면 복구 업로드가
불가능할 수 있으므로, 운영 배지에 적용하기 전에 테스트용 보드와 서명 키
백업을 사용해 별도 검증해야 합니다. ROM 진입 방식은 Espressif 공식
[Boot Mode Selection](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/advanced-topics/boot-mode-selection.html)을
참고하세요.

## 문제 해결

| 증상 | 확인할 내용 |
| --- | --- |
| `pio` 명령을 찾지 못함 | PlatformIO IDE 터미널을 사용하거나 Core 설치 후 shell PATH를 다시 엽니다. |
| 포트가 나타나지 않음 | 데이터 USB 케이블, 다른 USB 포트, `BOOT`+`EN` 복구 진입을 확인합니다. |
| `Connecting...`에서 멈춤 | Serial monitor를 닫고 올바른 포트를 지정한 뒤 BOOT/EN 절차를 다시 수행합니다. |
| 업로드 후 Serial이 안 보임 | 업로드 포트가 재연결될 때까지 기다린 뒤 `pio device list`를 다시 실행합니다. |
| 기본 문제를 수정했는데 예전 문제가 보임 | NVS 문제가 기본값보다 우선합니다. 관리자 편집을 사용하거나 전체 flash를 지웁니다. |
| 풀이 LED가 업로드 후에도 켜짐 | 정상적인 NVS 유지 동작입니다. 관리자 `RESET SOLVED`로 초기화합니다. |
| 배지는 발견되지만 인증되지 않음 | 펌웨어와 브리지의 `BADGE_ADMIN_KEY`가 같은지 확인합니다. |
| OLED가 비어 있음 | OLED 전원·납땜, SDA GPIO4, SCL GPIO5, I2C 주소 `0x3C`를 확인합니다. |

## 행사 전 배포 체크리스트

- `BADGE_ADMIN_KEY`를 개발 기본값에서 운영용 키로 교체합니다.
- 1~4번 기본 문제 또는 관리자 일괄 편집 내용을 확정합니다.
- 한 대에 먼저 업로드하고 USB 셸, OLED, 버튼, LED, 부저, Hidden Access,
  BLE 관리자 기능을 점검합니다.
- 전체 배지 업로드 후 관리자 대시보드에서 장비 ID와 인증 상태를 확인합니다.
- 테스트 중 생성된 풀이 상태는 `RESET ALL ONLINE`으로 초기화합니다.
- 부스 PC에서 OS별 관리자 시작 스크립트와 Bluetooth 권한을 사전 점검합니다.

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

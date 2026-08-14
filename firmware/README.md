# Hack The Badge Rev.3 Firmware

ESP32-S3-WROOM-1-N8R8용 펌웨어입니다. 기존
[`Z3r0c0k3/hacking-box`](https://github.com/Z3r0c0k3/hacking-box) 최신
`main` 커밋 `4b0b2cd`의 Serial 문제 흐름과 영구 상태 저장 방식을 Rev.3 PCB에
맞게 다시 구현했습니다.

## 구현 기능

- USB CDC Serial(115200): 문제 설명, FLAG 제출, 상태 확인
- 128x64 OLED: 문제 보기/예시, 3버튼 메뉴, 반응속도 미니게임
- LED1-LED5: 4개 Serial 문제와 `Hidden Access` 풀이 상태
- NVS: 전원을 꺼도 풀이 상태 유지
- `Hidden Access`: 전면 challenge pad의 올바른 두 접점을 1.2초간 쇼트하면 해금
- Wi-Fi 관리자: 부팅 중 `LEFT + RIGHT`를 1.5초간 누른 경우에만 임시 AP/웹/API 활성화

관리자 AP와 웹 비밀번호는 부팅할 때마다 무작위로 생성되어 OLED와 Serial에
표시됩니다. `http://192.168.4.1`에 접속하고 사용자명 `admin`을 사용합니다.
일반 부팅에서는 무선 기능이 켜지지 않습니다.

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

[`src/problems.h`](src/problems.h)의 `PROBLEMS` 배열만 수정합니다.

- `title`: OLED와 상태표에 표시할 짧은 ASCII 제목
- `answer`: Serial에서 비교할 정확한 FLAG
- `serialText`: Serial에 출력할 문제 설명
- `oledLines`: OLED에만 출력할 보기/예시 5줄(줄당 ASCII 16자 권장)

Rev.3 상태 LED가 5개이므로 기본 구성은 Serial 문제 4개 + Hidden Access 1개입니다.
문제 개수를 바꾸려면 LED 정책과 `static_assert`도 함께 검토해야 합니다.

미니게임 보상 힌트는 같은 파일의 `MINIGAME_REWARD_LINE_1/2`를 바꾸면 됩니다.

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

## 관리자 API

HTTP Basic 인증이 필요합니다.

| Method | Path | 기능 |
| --- | --- | --- |
| GET | `/api/status` | 풀이 상태 JSON |
| POST | `/api/solve?id=1` | 지정 문제 성공 처리(1~5) |
| POST | `/api/reset` | 전체 상태 초기화 |
| POST | `/api/reboot` | 재부팅 |

## 안전 및 핀 매핑

핀은 [`src/pins.h`](src/pins.h)에 있으며 PCB 회로 문서와 동일합니다. Hidden
Access 감지 중 C0는 LOW로만 구동되고 C1/C2는 pull-up 입력입니다. 펌웨어의
의도된 쇼트 대상은 보호 저항 뒤의 challenge pad뿐입니다. `3V3`, `VBUS`,
`EN`, `BOOT` 또는 GND를 임의로 쇼트하지 마세요.

OLED는 전체 1 KB framebuffer 대신 U8x8 text mode를 사용하고, Serial 입력도
고정 192바이트 버퍼를 사용해 동적 메모리 사용을 줄였습니다.

## 빠른 로직 검사

PlatformIO 없이도 상태 비트와 Hidden Access 판정 로직을 검사할 수 있습니다.

```bash
clang++ -std=c++17 -Ifirmware/src firmware/test/test_logic.cpp -o /tmp/badge-logic-test
/tmp/badge-logic-test
```

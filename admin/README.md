# AEGIS BLE Badge Admin

Windows, macOS, Linux PC가 Bluetooth LE Central로 각 배지에 P2P 연결됩니다.
`bridge.py`가 BLE 연결, HTTP API, 웹 대시보드를 한 프로세스에서
제공하므로 Docker, 공유기, 인터넷 연결은 필요하지 않습니다.
웹 서버는 관리자 PC의 `127.0.0.1:8080`에만 바인딩됩니다.

## 준비 사항

공통으로 Python 3.10 이상과 Bluetooth LE 어댑터가 필요합니다. 자동 실행기는
Python 가상환경과 pip 패키지만 준비하며 Python, Bluetooth 드라이버,
Linux 시스템 패키지는 설치하지 않습니다.

- Windows: Windows 10/11, Bluetooth LE 어댑터, `python` 또는 `py` 명령
- macOS: macOS 10.15 이상. 첫 실행 시 Terminal/Python의 Bluetooth 권한 허용
- Linux: BlueZ 5.55 이상, D-Bus, Python venv 모듈. Debian/Ubuntu 예시:

```bash
sudo apt install python3 python3-venv bluez
```

## OS별 자동 실행

스크립트는 첫 실행 시 `admin/.venv`를 생성하고,
`requirements.txt`의 `aiohttp`, `bleak`, `pyserial`이 없거나 목록이 바뀌었을 때만
pip로 설치합니다. 그 다음 프로토콜 자가 검사를 통과하면 서버를
시작합니다. 운영 키는 환경변수 또는 `--admin-key` 인자로 전달하고, 공개
개발 키로 로컬 테스트할 때만 `--allow-dev-key`를 붙입니다.

macOS:

```bash
cd admin
./start-macos.sh
```

Linux:

```bash
cd admin
./start-linux.sh
```

Windows Command Prompt/PowerShell:

```bat
cd admin
start-windows.bat
```

Windows에서는 `start-windows.bat`을 더블 클릭해도 됩니다. 실행 후 터미널에
다음 주소가 표시되면 브라우저로 엽니다.

```text
http://127.0.0.1:8080
```

설치와 자가 검사만 수행하고 서버를 실행하지 않으려면 각 명령 뒤에
`--check`를 붙입니다. 예: `./start-macos.sh --check`, `start-windows.bat --check`.

## 대시보드 사용법

1. 배지 전원과 PC Bluetooth를 켭니다.
2. 브리지를 실행한 뒤 `DISCOVERED BADGES`에서 배지를 선택합니다.
3. `ONLINE` 및 `AUTHENTICATED`가 표시되면 관리 기능을 사용합니다.

| 화면 | 기능 |
| --- | --- |
| `SOLVED`, `SERIAL`, `HIDDEN` | 전체, 1~4번, Hidden Access 풀이 상태 |
| `MARK ALL SOLVED` | 선택한 배지를 5/5로 처리하고 Trophy 이벤트 실행 |
| `RESET SOLVED` | 해당 배지의 모든 풀이 상태 초기화 |
| `REBOOT` | 해당 배지 재부팅 |
| `BUZZER VOLUME` | 선택한 배지의 전체 효과음 크기를 1~10으로 조절·저장 |
| `EDIT PROBLEMS` | 1~4번 문제 조회·수정 |
| `EDIT ALL ONLINE` | 현재 인증·연결된 모든 배지의 동일한 문제 일괄 수정 |
| `RESET ALL ONLINE` | 현재 인증·연결된 모든 배지의 풀이 상태 초기화 |
| `REBOOT ALL ONLINE` | 현재 인증·연결된 모든 배지 재부팅 |
| 하단 터미널 | BLE 관리자 셸 |

대시보드의 상태 갱신은 브리지 메모리의 최신 상태를 조회하며,
주기적인 `status` 명령을 관리자 셸 로그에 출력하지 않습니다.

## 리더보드 디스플레이

관리 기능이 없는 전용 화면은 브리지 실행 후 다음 주소로 접속합니다.

```text
http://127.0.0.1:8080/leaderboard
```

Flappy Hacker, Firewall Breaker, Tetris Stack Top 10을 표시하며 1초마다
SQLite DB의 최신 상태를 가져와 페이지 새로고침 없이 갱신합니다.
1~10글자 닉네임은 굵게, 배지는 `AEGIS-`를 제외한 고유값만 표시됩니다.

게임 종료 시 배지가 점수를 보고하면 브리지가 **전체 배지의 해당 게임
최고점**과 비교합니다. 새 최고점일 때만 배지 OLED에서 닉네임 입력을
요청하고, 입력 완료 후 `admin/scores.db`에 저장합니다. DB는 브리지와
함께 재시작하거나 배지가 오프라인이어도 유지되며 `.gitignore` 대상입니다.
다른 경로를 사용하려면 실행 전에 `AEGIS_SCORE_DB` 환경변수를 지정합니다.

세 게임의 OLED `BEST`도 서버의 게임별 1위 이름·점수입니다. 인증 시와
점수 저장 후 연결된 배지에 동기화하며, DB에 기록이 없으면 `0 / ---`로
초기화합니다. 보드는 이름 제출만으로 최고점을 변경하지 않습니다.
기존 배지별 개인 최고점 행은 보관하며 동점은 갱신하지 않습니다.
서버 연결이 없으면 새 점수 등록을 생략하고 마지막으로 동기화한 BEST를
표시합니다(재부팅 시에는 `0 / ---`).

닉네임 입력은 **공백부터 시작**하며 방향키로 `공백 → A-Z → 0-9`를
순환합니다. `OK`를 짧게 누르면 현재 글자(공백 포함)를 확정하고 다음
공백 칸으로 이동합니다. `OK`를 700ms 길게 누르면 **커서 앞까지 확정한
글자만** 제출하고 현재 커서의 글자는 제외합니다. 10글자 뒤 빈 칸은 저장
전용입니다. 확정한 공백은 그대로 보존하며 공백만 있는 이름은 제출할 수 없습니다.
`LEFT`+`RIGHT`를 동시에 700ms 누른 뒤 손을 떼면 저장 없이
**메인화면(Home)**으로 돌아갑니다. 입력 중 BLE 연결이 끊겨도
등록을 취소하고 Home으로 돌아갑니다.

## HG-ESP32-S3 DevkitC-1 Morse Link

DevkitC-1 한 대를 PC의 USB ↔ ESP-NOW 어댑터로 사용합니다.
배지의 Morse Link v3와 같은 무선 패킷을 사용하며 OLED나 추가 배선,
공유기는 필요하지 않습니다. 기존 배지 BLE 관리 기능과 함께 동작합니다.

보드의 GPIO38 RGB LED는 모스 부호를 **송신할 때 빨강**, **수신할 때
파랑**으로 부호 길이만큼 켜집니다(기본 점 100ms / 선 300ms).
대기·문자/단어 간격에는 꺼지고, 송수신이 겹치면 마지막 부호의 색을
표시합니다. `firmware/src/morse_adapter.cpp`의 `MORSE_LED_BRIGHTNESS`
(기본 32, 범위 0~255)로 밝기를 조절할 수 있습니다.
[DevKitC-1 v1.1은 GPIO38, 초기 버전은 GPIO48](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)을
사용하므로 보드가 GPIO48 버전이면 `MORSE_LED_PIN`을 48로 바꾸세요.

1. 저장소 루트에서 어댑터 전용 펌웨어를 빌드·업로드합니다.

   ```bash
   pio run -d firmware -e morse-bridge-s3
   pio run -d firmware -e morse-bridge-s3 -t upload --upload-port /dev/cu.usbmodemXXXX
   ```

2. PC에는 보드의 **ESP32-S3 native USB 포트**를 연결합니다. USB-UART
   포트와 구분하세요. 이 환경의 실행 중 통신은 native USB CDC입니다.
   포트 구성은 [Espressif DevkitC-1 안내](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html)를 참고하세요.
3. 브리지를 시작합니다. USB 포트는 웹에서 선택할 수 있으며 관리자 키는
   기존 방식대로 전달합니다. 시작부터 연결하려면 `--morse-port`를 지정합니다.

   ```bash
   cd admin
   ./start-macos.sh
   # Linux: ./start-linux.sh
   # Windows: start-windows.bat
   # 시작 시 자동 연결: ./start-macos.sh --morse-port /dev/cu.usbmodemXXXX --morse-channel 1
   ```

4. 대시보드의 `MORSE LINK` 또는 `http://127.0.0.1:8080/morse`를 엽니다.
   `REFRESH`로 서버 PC의 시리얼 장치 목록을 불러오고 `DEVICE`에서 Morse
   어댑터를 선택한 뒤 `CONNECT`를 누릅니다. 포트명·설명·USB 시리얼 번호가
   표시되므로 배지와 어댑터의 USB 설명이 같아도 구분할 수 있습니다.
   `ONLINE` 확인 후 배지와 같은 채널(1~13)을 선택하고 `APPLY`합니다.
   영문·숫자·공백 최대 40자를 입력하고 `SEND`하면 모스로 송신합니다.
   수신 화면에는 발신 배지 고유값별 번역과 현재 모스 부호가 표시됩니다.

포트는 `AEGIS_MORSE_PORT`, 시작 채널은 `AEGIS_MORSE_CHANNEL` 환경변수로도
지정할 수 있습니다. 미지정 시 웹에서 장치를 선택할 때까지 USB 포트를
열지 않습니다. 목록 조회도 장치를 열거나 자동 연결하지 않습니다.
선택한 장치가 Morse 어댑터의 `READY 3` 응답을 보내야 `ONLINE`이 되며,
일반 배지를 선택하면 어댑터 확인 오류를 표시하고 모스 송신을 막습니다.
포트 연결 실패나
USB 분리 시 화면에 오류를 표시하고 2초 간격으로 같은 포트에 재연결합니다.
포트 이름이 달라지면 웹에서 `REFRESH` 후 새 포트를 선택하세요.
`DISCONNECT`는 포트를 닫고 자동 재연결도 중지합니다. 웹에서 선택한 포트는
현재 서버 실행 동안 유지되고 재시작 시에는 시작 옵션/환경변수를 사용합니다.

송신 중에는 장치 변경·연결 해제·채널 변경과 추가 송신을 막습니다. `TX COMPLETE`는 무선
송신 완료이며 상대 배지의 수신 확인은 아닙니다. 중간 실패 시 일부 문자만
전송되었을 수 있습니다. 어댑터는 선택한 한 채널만 수신하며 배지처럼
100ms dit / 300ms dah / 300ms 문자 간격 / 700ms 단어 간격을 사용합니다.

USB 줄 프로토콜(115200 baud): `HELLO`, `CHANNEL 1`~`13`,
`TX <ASCII code> <duration ms>`; 응답은 `READY 3 <channel> <id>`,
`OK TX`, `ERR ...`, 수신은 `RX <sender> <ASCII code> <duration ms>`입니다.
ASCII code는 dit 46, dah 45, 문자 경계 47, 단어 경계 32입니다.
경계의 duration은 0이고 부호는 30~2000ms만 허용합니다.

하드웨어 없이 점수 동기화·HTTP API·가상 USB 어댑터의 송수신/재연결을
검증하려면 저장소 루트에서 실행합니다(운영 DB는 사용하지 않습니다).

```bash
admin/.venv/bin/python admin/test_bridge.py
python3 firmware/test/test_morse_led.py
```

업로드 시 `device reports readiness to read but returned no data`가 발생하면
먼저 웹에서 `DISCONNECT`를 누르거나 브리지 터미널을 `Ctrl+C`로 종료하고
Serial Monitor도 닫습니다. 브리지가 자동 재연결 중인 상태에서는 포트가
잠시 닫혀 있어도 다시 점유할 수 있습니다. macOS에서는
`lsof /dev/cu.usbmodemXXXX`로 다른 프로세스가 포트를 열고 있는지 확인한 뒤
`--upload-port`에 해당 포트를 지정해 업로드하세요.
[Espressif도 시리얼 예외 원인으로 다른 프로그램의 포트 점유를 안내합니다.](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/troubleshooting.html#a-serial-exception-error-occurred)
점유를 해제해도 `Connecting...`에서 실패하면 `BOOT`를 누른 채 `RESET/EN`을
눌렀다 떼고 `BOOT`도 뗀 뒤 포트 목록을 다시 확인해 업로드합니다.
[ESP32-S3 수동 다운로드 모드 안내](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/advanced-topics/boot-mode-selection.html#manual-bootloader).
업로드 후 필요하면 `RESET`을 한 번 누르고 웹에서 `REFRESH → CONNECT`합니다.

## 관리자 셸

대시보드에서 배지를 선택하면 다음 명령을 무선으로 실행할 수 있습니다.
USB Serial 사용자 셸과 BLE 관리자 셸은 입력 상태를 서로 따로 유지합니다.
두 셸의 1~4번 문제 플레이는 같은 대화형 Challenge Engine을 사용하므로
HEX 표시, 디버그/진단 명령, Legacy Auth 동작이 동일합니다.

| 명령 | 기능 |
| --- | --- |
| `help` | 명령 목록 |
| `status` | 장비 ID와 문제 풀이 상태 갱신 |
| `solve all` | 모든 Challenge를 해결 처리하고 Trophy/fanfare 실행 |
| `reset` | 모든 풀이 상태 초기화 |
| `reboot` | 배지 재부팅 |
| `volume 1`~`10` | 버저 음량 저장 및 새 음량으로 테스트음 재생 |
| `1`~`4` | USB와 동일한 문제 선택 |
| `hint`, `exit`, `clear`, `aegis` | USB 사용자 셸과 동일한 기능 |

## 문제 편집

`EDIT PROBLEMS`는 선택한 배지만, `EDIT ALL ONLINE`은 현재 인증·연결된
모든 배지를 동일한 내용으로 수정합니다. 두 모드 모두 1~4번만
수정할 수 있으며 Hidden Access는 편집 대상이 아닙니다. 저장한 문제는
배지 NVS에 유지되고, 수정된 문제의 기존 풀이 상태만 초기화됩니다.

- 선택형: ASCII 보기 2~4개와 정답 번호 1~4
- FLAG형: FLAG 문자열과 OLED에 표시할 `보기` 문구 0~4개
- Mission 04의 `ANSWER / REWARD FLAG`는 직접 제출할 정답이 아니라,
  동적 challenge-response 인증 성공 후 출력되는 보상 FLAG입니다.
- 제한: 제목 23 bytes, 문제 본문 255 bytes, 정답 79 bytes,
  OLED 보기/문구 각 23 bytes
- OLED 폰트 제약으로 제목과 OLED 보기/문구는 ASCII만 허용

## 관리자 키

기본 개발 키는 `AEGIS_DEV_ONLY_CHANGE_ME`입니다. 실제 행사 전
소스의 기본값을 직접 바꾸지 말고, 펌웨어 빌드와 브리지에 동일한
`BADGE_ADMIN_KEY`를 주입합니다. 운영 키 생성부터 펌웨어 업로드까지의
전체 절차는 [펌웨어 프로덕션 배포](../firmware/README.md#최종-프로덕션-배포)를
따릅니다.

macOS/Linux:

```bash
export BADGE_ADMIN_KEY='AEGIS_DEV_ONLY_CHANGE_ME'
./start-macos.sh # Linux는 ./start-linux.sh

# 또는 실행 인자로 전달
./start-macos.sh --admin-key 'AEGIS_DEV_ONLY_CHANGE_ME'
```

Windows Command Prompt:

```bat
set BADGE_ADMIN_KEY=AEGIS_DEV_ONLY_CHANGE_ME
start-windows.bat

start-windows.bat --admin-key "AEGIS_DEV_ONLY_CHANGE_ME"
```

Windows PowerShell:

```powershell
$env:BADGE_ADMIN_KEY='AEGIS_DEV_ONLY_CHANGE_ME'
.\start-windows.bat

.\start-windows.bat --admin-key 'AEGIS_DEV_ONLY_CHANGE_ME'
```

키 원문은 BLE로 전송되지 않고, 연결마다 새 challenge를 사용한
상호 HMAC-SHA256 증명에만 사용됩니다. 공개 개발 키로 브리지를 실행하려면
로컬 테스트임을 명시하는 `--allow-dev-key`가 필요하며, 운영 키는 최소
32 UTF-8 bytes여야 합니다. 현재 구성은 모든 배지가 하나의 fleet key를
공유합니다. `--admin-key` 값은 브리지 프로세스의 인자에는 남지 않지만
쉘 명령 기록에는 남을 수 있으므로 공용 PC에서는 환경변수를 권장합니다.

```bash
./start-macos.sh --allow-dev-key # 개발용 배지에만 사용
```

인증 프로토콜이 변경되었으므로 펌웨어와 브리지는 같은 버전으로
업데이트해야 합니다.

## 종료와 문제 해결

서버는 실행 중인 터미널에서 `Ctrl+C`로 종료합니다.

- `Address already in use`: 8080 포트를 사용 중인 기존 서버를 종료합니다.
- 배지가 보이지 않음: PC와 배지의 Bluetooth를 켜고 가까이 두 뒤,
  OS의 Bluetooth 권한과 어댑터 상태를 확인합니다.
- macOS 권한 거부: 시스템 설정의 개인정보 보호 및 보안 > Bluetooth에서
  사용 중인 터미널 앱을 허용합니다.
- Linux 권한/BlueZ 오류: Bluetooth 서비스가 실행 중인지, 사용자가
  D-Bus Bluetooth 접근 권한을 갖는지 확인합니다.
- Python 가상환경 생성 실패: Python 3.10 이상과 `venv`/`ensurepip`
  모듈이 설치되었는지 확인합니다.

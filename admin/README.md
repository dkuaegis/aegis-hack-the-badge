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
`requirements.txt`의 `aiohttp`와 `bleak`가 없거나 목록이 바뀌었을 때만
pip로 설치합니다. 그 다음 프로토콜 자가 검사를 통과하면 서버를
시작합니다.

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
| `EDIT PROBLEMS` | 1~4번 문제 조회·수정 |
| `EDIT ALL ONLINE` | 현재 인증·연결된 모든 배지의 동일한 문제 일괄 수정 |
| `RESET ALL ONLINE` | 현재 인증·연결된 모든 배지의 풀이 상태 초기화 |
| `REBOOT ALL ONLINE` | 현재 인증·연결된 모든 배지 재부팅 |
| 하단 터미널 | BLE 관리자 셸 |

대시보드의 상태 갱신은 브리지 메모리의 최신 상태를 조회하며,
주기적인 `status` 명령을 관리자 셸 로그에 출력하지 않습니다.

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
`firmware/src/main.cpp`의 `BADGE_ADMIN_KEY` 기본값을 바꿔 펌웨어를
다시 업로드하고 브리지에도 동일한 값을 설정합니다.

macOS/Linux:

```bash
export BADGE_ADMIN_KEY='replace-with-a-long-random-event-key'
./start-macos.sh # Linux는 ./start-linux.sh
```

Windows Command Prompt:

```bat
set BADGE_ADMIN_KEY=replace-with-a-long-random-event-key
start-windows.bat
```

Windows PowerShell:

```powershell
$env:BADGE_ADMIN_KEY='replace-with-a-long-random-event-key'
.\start-windows.bat
```

키 원문은 BLE로 전송되지 않고, 연결마다 새 challenge를 사용한
HMAC-SHA256 응답에만 사용됩니다. 현재 구성은 모든 배지가 하나의
fleet key를 공유합니다.

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

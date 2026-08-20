# Hack The Badge Ver.3

## Sponsored by

<p align="center">
  <a href="https://easyeda.com/">
    <img src="assets/brand/sponsors/official-kit/easyeda/EasyEDA_Horz_Blue_Trans.png" alt="EasyEDA" height="48">
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://jlcpcb.com/">
    <img src="assets/brand/sponsors/official-kit/jlcpcb/JLCPCB-logo-Blue.svg" alt="JLCPCB" height="48">
  </a>
</p>

해당 프로젝트는 EasyEDA로 제작되었고 EasyEDA 측의 제작 지원을 받았습니다. <br>
PCB 제작은 JLCPCB 측의 지원을 받았습니다.

## 프로젝트 소개

`Hack The Badge Ver.3`는 정보보안 동아리 Aegis가 MSG CTF 본선
부스에서 운영하는 체험형 하드웨어 해킹 프로젝트입니다. ESP32-S3를
기반으로 OLED, 버튼, LED, USB Serial, UART, challenge pad, 부저를
하나의 PCB 배지에 구성해, 행사 배지와 해킹 문제 도구로 함께 사용할
수 있도록 제작했습니다.

## 제작 목적

참가자가 일반적인 소프트웨어 CTF를 넘어 실제 PCB의 입출력 장치와
통신 인터페이스를 직접 살펴보며 하드웨어 보안을 체험하도록 하는 것이
목표입니다. 문제 풀이 결과가 화면, LED, 소리로 즉시 반영되는 상호작용을
통해 하드웨어 해킹을 처음 접하는 참가자도 쉽게 몰입할 수 있도록
구성했습니다.

## 체험 활동

참가자는 배지를 USB로 연결한 뒤 다음 활동을 진행합니다.

- Serial 터미널에서 문제를 확인하고 FLAG를 제출합니다.
- OLED와 버튼으로 문제, 힌트, 미니게임을 이용합니다.
- UART와 challenge pad를 분석해 숨겨진 하드웨어 문제를 해결합니다.
- OLED, LED, 부저를 통해 문제 진행 상태와 완료 결과를 확인합니다.

## 현재 제작 리비전

- 리비전: Hack The Badge Ver.3
- MCU: ESP32-S3-WROOM-1-N8R8
- 디스플레이: HS96L03W2C03 0.96 inch I2C OLED, PCBA 이후 수작업 납땜
- 사용자 I/O: USB Serial, 3.3 V UART, 버튼 3개, 상태 LED 5개
- Challenge I/O: 1 kOhm 직렬 저항으로 보호되는 `C0`, `C1`, `C2` GPIO pad
- 관리자/디버그: 복구와 bring-up을 위한 후면 staff test pad
- 오디오: MOSFET으로 구동하는 passive buzzer
- PCB 스타일: 검정 solder mask, 흰색 silkscreen, Aegis 방패 외형

## 저장소 구조

```text
assets/brand/                         Aegis, MSG CTF, EasyEDA, JLCPCB 로고
docs/rev3/                            설계, 제작, 스폰서 관련 문서
hardware/design/rev3/kicad/           KiCad 호환 회로도, PCB, 라이브러리
hardware/design/rev3/reference/       BOM 메모, 데이터시트, 전기적 설계 메모
hardware/releases/rev3/jlcpcb/upload/ JLCPCB 업로드용 Gerber, BOM, CPL
hardware/releases/rev3/easyeda-pro/   EasyEDA Pro 프로젝트 패키지와 체크리스트
hardware/releases/rev3/jlcpcb/        제작 파일, 조립 파일, preview, 검증 리포트
archive/                              이전 설계/제작 이력
tools/                                문서 생성 보조 스크립트
firmware/                             ESP32-S3 문제/UI/관리자 펌웨어
admin/                                Python BLE 브리지와 로컬 웹 대시보드
player-console/                       플레이어용 Web Serial 콘솔과 Docker 배포 구성
```

펌웨어 빌드, 문제 교체, Serial 명령과 무선 관리자 사용법은
[`firmware/README.md`](firmware/README.md)를 참고하세요.
브리지 설치, OS별 실행법과 운영 안내는
[`admin/README.md`](admin/README.md)를 참고하세요.
플레이어용 브라우저 USB 콘솔의 Docker 실행과 HTTPS 배포 안내는
[`player-console/README.md`](player-console/README.md)를 참고하세요.

## 펌웨어 빠른 시작

펌웨어 대상은 `ESP32-S3-WROOM-1-N8R8`이며 PlatformIO 환경 이름은
`esp32-s3-rev3`입니다. 데이터 통신이 가능한 USB-C 케이블로 배지를 연결한
뒤 저장소 루트에서 다음 명령을 실행합니다.

```bash
cd firmware
pio run
pio device list
pio run -t upload
pio device monitor
```

`pio run`은 첫 실행 시 ESP32 플랫폼, Arduino framework와 U8g2 의존성을
자동으로 내려받아 빌드합니다. Serial monitor 속도는 `platformio.ini`에
`115200`으로 설정되어 있습니다. 포트 자동 선택이 실패하면 OS에서 확인한
포트를 직접 지정합니다.

```bash
# Windows 예시
pio run -t upload --upload-port COM5
pio device monitor --port COM5

# macOS 예시
pio run -t upload --upload-port /dev/cu.usbmodemXXXX
pio device monitor --port /dev/cu.usbmodemXXXX

# Linux 예시
pio run -t upload --upload-port /dev/ttyACM0
pio device monitor --port /dev/ttyACM0
```

업로드 포트가 나타나지 않으면 USB 케이블이 충전 전용인지 먼저 확인하고,
`BOOT` 버튼을 누른 상태에서 `EN`을 눌렀다 놓은 뒤 `BOOT`를 놓아 ROM 다운로드
모드로 진입한 다음 다시 업로드합니다. 일반 업로드는 NVS를 지우지 않으므로
기존 풀이 상태와 관리자 페이지에서 편집한 문제는 유지됩니다.

PlatformIO 설치, 완전 초기화, BOOT 복구, 업로드 후 점검, 핀 매핑과 보안
주의사항은 [`firmware/README.md`](firmware/README.md)의 상세 절차를
참고하세요.

## 소프트웨어 구조

참가자 USB Serial과 관리자 BLE 셸은 각자의 입력 상태를 따로 유지합니다.
관리자 PC에서는 하나의 Python 프로세스가 BLE Central, HTTP API,
정적 대시보드를 모두 제공합니다. 인터넷과 공유기는 필요하지 않고,
브라우저는 관리자 PC의 `127.0.0.1` 주소로만 접속합니다.

| 코드 | 역할 |
| --- | --- |
| `firmware/src/main.cpp` | 메인 루프, OLED UI, 버튼·LED, USB/BLE 셸, 미니게임, challenge pad 처리 |
| `firmware/src/problems.h` | 1~4번 기본 문제, 문제 크기 제한, 미니게임 보상 문구 |
| `firmware/src/pins.h` | Rev.3 PCB의 GPIO 매핑 |
| `firmware/src/logic.h` | 상태 비트와 challenge pad 판정 로직 |
| `admin/bridge.py` | 배지 탐색·인증·연결, HTTP API, 대시보드 서빙 |
| `admin/dashboard/index.html` | 배지별 상태, 관리자 셸, 리셋·재부팅·문제 편집 UI |
| `admin/start.py` | 가상환경 생성, pip 의존성 확인·설치, 자가 검사, 서버 실행 |
| `player-console/` | 관리자 기능 없이 브라우저와 USB CDC를 직접 연결하는 정적 웹 콘솔 |

## 참가자 사용 설명서

1. 배지를 USB로 PC에 연결하고 Serial 터미널을 `115200 baud`로 엽니다.
2. `aegis`를 입력한 뒤 `1`~`4`로 문제를 선택합니다.
3. 한국어 문제 본문은 Serial에서, 영문 ASCII 힌트는 OLED에서 확인합니다.
4. 문제 안내에 따라 문제 내부 명령 또는 FLAG를 Serial에 입력합니다.
5. 해결한 문제는 상태 LED와 OLED `STATUS`에 반영됩니다.

Serial 명령:

| 명령 | 기능 |
| --- | --- |
| `1`~`4` | 문제 선택 |
| `hint` | 선택한 문제의 OLED 보기/예시 재표시 |
| `exit` | 현재 문제 나가기 |
| `status` | 문제 풀이 상태 표시 |
| `help` | 사용 가능한 명령 표시 |
| `clear` | Serial 터미널 화면 정리 |
| `aegis` | 시작 배너 재표시 |

OLED 하단의 `LEFT`, `OK`, `RIGHT` 버튼으로 메뉴 이동과 Flappy Hacker를
조작합니다. 미니게임에서 목표 점수를 넘기면 OLED에 추가 힌트가
표시됩니다.

## 관리자 사용 설명서

Python 3.10 이상과 Bluetooth LE가 가능한 PC에서 해당 OS의 스크립트를
실행합니다. 첫 실행 시 `admin/.venv`를 만들고 필요한 pip 패키지를
자동 설치한 뒤 브리지를 시작합니다.

```bash
# macOS
./admin/start-macos.sh

# Linux
./admin/start-linux.sh
```

Windows에서는 터미널에서 `admin\start-windows.bat`을 실행하거나 파일을
더블 클릭합니다. 시작 후 브라우저에서 `http://127.0.0.1:8080`을 엽니다.

대시보드에서 배지를 선택하면 다음 작업을 수행할 수 있습니다.

- 1~4번과 Hidden Access의 풀이 상태 확인
- 개별 또는 현재 연결된 전체 배지의 풀이 상태 초기화·재부팅
- USB 사용자 셸 기능을 포함한 BLE 관리자 셸 사용
- 1~4번 문제의 FLAG/최대 4지선다 유형 개별·일괄 수정

행사 전에는 펌웨어와 브리지의 `BADGE_ADMIN_KEY`를 동일한 운영용
키로 교체하세요. 자세한 OS별 준비, 설정, 문제 편집 제한과 문제 해결은
[`admin/README.md`](admin/README.md)에 정리했습니다.

## 제작 산출물

JLCPCB 업로드 파일:

| 단계     | 파일                                                                       |
| -------- | -------------------------------------------------------------------------- |
| PCB 제작 | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_gerbers.zip` |
| PCBA BOM | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_bom.csv`     |
| PCBA CPL | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_cpl.csv`     |

EasyEDA Pro 프로젝트 패키지:

| 용도                             | 파일                                                                                            |
| -------------------------------- | ----------------------------------------------------------------------------------------------- |
| EasyEDA Pro 실크 호환 프로젝트   | `hardware/releases/rev3/easyeda-pro/upload/hacking_badge_v3_easyeda_pro_silk_compat_import.zip` |
| EasyEDA Pro 프로젝트(KiCad 호환) | `hardware/releases/rev3/easyeda-pro/upload/hacking_badge_v3_easyeda_pro_kicad_import.zip`       |
| EasyEDA Pro 프로젝트 아카이브    | `hardware/releases/rev3/easyeda-pro/reference/ProPrj_hack_the_badge_rev.3.epro2`                |

## 3D Preview

홍보물 제작이나 웹/Blender preview에는 검정 PCB 색상이 보정된 GLB 파일을
사용하는 것을 권장합니다.

| 용도                    | 파일                                                                                |
| ----------------------- | ----------------------------------------------------------------------------------- |
| 검정 PCB 홍보용 GLB     | `hardware/releases/rev3/jlcpcb/preview/3d/hacking_badge_v3_full_assembly_black.glb` |
| 검정 PCB 3D export 묶음 | `hardware/releases/rev3/jlcpcb/preview/3d/hacking_badge_v3_3d_exports_black.zip`    |
| 전체 3D export 묶음     | `hardware/releases/rev3/jlcpcb/preview/3d/hacking_badge_v3_3d_exports.zip`          |

## 검증 상태

현재 확인된 상태:

- Schematic ERC: 0 errors, 0 warnings
- Schematic-to-PCB validation: PASS
- JLCPCB manufacturing validation: PASS
- Gerber ZIP SHA256:
  `b55b42de45568e995e8cb47bb18cfc09abd5469c50e1fb60852d323a703e96b1`

유용한 검증 명령:

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc \
  --format report \
  -o hardware/design/rev3/kicad/reports/erc-final.rpt \
  hardware/design/rev3/kicad/hacking_box_v2.kicad_sch

/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 \
  hardware/design/rev3/kicad/scripts/validate_schematic_against_pcb.py

/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 \
  hardware/design/rev3/kicad/scripts/validate_manufacturing.py
```

## 참고 사항

- KiCad 파일명은 초기 프로젝트/라이브러리 이름을 유지하기 위해
  `hacking_box_v2`를 사용합니다. 실제 제작 리비전은 Ver.3입니다.
- `OLED1`은 JLCPCB BOM/CPL에서 제외되어 있으며, 별도 구매 후 수작업으로
  납땜하는 기준입니다.
- JLCPCB SMT viewer에서 자동 placement alignment 알림이 뜨면 취소하고,
  기존 CPL 기준 배치가 유지되는지 확인합니다. 방패 형태의 custom outline
  때문에 false offset warning이 뜰 수 있습니다.
- Challenge pad는 3.3 V GPIO 전용입니다. 회로를 의도적으로 수정하지 않은
  상태에서 `VBUS`, `3V3`, `EN`, `BOOT` 단락을 문제 풀이 요소로 노출하지
  마세요.

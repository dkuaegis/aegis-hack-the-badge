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

해당 프로젝트는 EasyEDA로 제작되었고 EasyEDA 측의 제작 지원을
받았습니다. PCB 제작은 JLCPCB 측의 지원을 받았습니다.

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
```

펌웨어 빌드, 문제 교체, Serial 명령과 무선 관리자 사용법은
[`firmware/README.md`](firmware/README.md)를 참고하세요.

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

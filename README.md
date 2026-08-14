# Hack The Badge Ver.3

MSG CTF 본선 동아리 부스 체험존에서 사용할 `Aegis x MSG CTF`
하드웨어 배지 프로젝트입니다. ESP32-S3 기반 보드에 OLED, 상태 LED,
버튼, UART, USB Serial, 부저, challenge GPIO pad를 올려 참가자가 직접
보드를 분석하고 문제를 해결하는 형태로 설계했습니다.

## Sponsored By

<p align="center">
  <a href="https://easyeda.com/">
    <img src="assets/brand/sponsors/official-kit/easyeda/EasyEDA_Horz_Blue_Trans.png" alt="EasyEDA" height="48">
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://jlcpcb.com/">
    <img src="assets/brand/sponsors/official-kit/jlcpcb/JLCPCB-logo-Blue.svg" alt="JLCPCB" height="48">
  </a>
</p>

이 프로젝트는 EasyEDA와 JLCPCB의 지원을 받아 제작되었습니다. 공개
GitHub 프로젝트 README 요구사항에 맞춰 위 스폰서 로고는 각 공식
웹사이트로 연결됩니다.

## 현재 제작 리비전

- 리비전: Hack The Badge Ver.3
- MCU: ESP32-S3-WROOM-1-N8R8
- 디스플레이: HS96L03W2C03 0.96 inch I2C OLED, PCBA 이후 수작업 납땜
- 사용자 I/O: USB Serial, 3.3 V UART, 버튼 3개, 상태 LED 5개
- Challenge I/O: 1 kOhm 직렬 저항으로 보호되는 `C0`, `C1`, `C2` GPIO pad
- 관리자/디버그: 복구와 bring-up을 위한 후면 staff test pad
- 오디오: MOSFET으로 구동하는 passive buzzer
- PCB 스타일: 검정 solder mask, 흰색 silkscreen, Aegis 방패 외형

라우팅된 제작 PCB의 기준 원본은 편집 가능한 KiCad 프로젝트입니다.
EasyEDA Pro 패키지는 스폰서/쿠폰 워크플로우를 위해 준비한 별도
변환본이며, EDA 포맷 변환 과정에서 copper zone이나 표시 결과가 달라질
수 있으므로 import 이후 반드시 다시 확인해야 합니다.

## 저장소 구조

```text
assets/brand/                         Aegis, MSG CTF, EasyEDA, JLCPCB 로고
docs/rev3/                            설계, 제작, 스폰서 관련 문서
hardware/design/rev3/kicad/           편집 가능한 KiCad 회로도, PCB, 라이브러리
hardware/design/rev3/reference/       BOM 메모, 데이터시트, 전기적 설계 메모
hardware/releases/rev3/jlcpcb/upload/ JLCPCB 업로드용 Gerber, BOM, CPL
hardware/releases/rev3/easyeda-pro/   EasyEDA Pro import 패키지와 체크리스트
hardware/releases/rev3/jlcpcb/        제작 파일, 조립 파일, preview, 검증 리포트
archive/                              이전 설계/제작 이력
tools/                                문서 생성 보조 스크립트
firmware/                             ESP32-S3 문제/UI/관리자 펌웨어
```

펌웨어 빌드, 문제 교체, Serial 명령과 무선 관리자 사용법은
[`firmware/README.md`](firmware/README.md)를 참고하세요.

## 제작 산출물

JLCPCB 업로드 파일:

| 단계 | 파일 |
| --- | --- |
| PCB 제작 | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_gerbers.zip` |
| PCBA BOM | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_bom.csv` |
| PCBA CPL | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_cpl.csv` |

EasyEDA Pro import 패키지:

| 용도 | 파일 |
| --- | --- |
| 실크 호환 처리가 포함된 권장 EasyEDA Pro import 파일 | `hardware/releases/rev3/easyeda-pro/upload/hacking_badge_v3_easyeda_pro_silk_compat_import.zip` |
| 비교용 원본 KiCad import 파일 | `hardware/releases/rev3/easyeda-pro/upload/hacking_badge_v3_easyeda_pro_kicad_import.zip` |
| 이전 EasyEDA Pro 프로젝트 archive 참고본 | `hardware/releases/rev3/easyeda-pro/reference/ProPrj_hack_the_badge_rev.3.epro2` |

실제 제작은 EasyEDA Pro 변환본을 시각적/전기적으로 재검증하기 전까지
JLCPCB release package를 기준으로 진행합니다. 권장 EasyEDA Pro ZIP은
EasyEDA import 과정에서 채워진 로고 실크가 빈 외곽선처럼 보이지 않도록,
filled silkscreen 로고를 촘촘한 line artwork로 변환한 버전입니다.

## 3D Preview

홍보물 제작이나 웹/Blender preview에는 검정 PCB 색상이 보정된 GLB 파일을
사용하는 것을 권장합니다.

| 용도 | 파일 |
| --- | --- |
| 검정 PCB 홍보용 GLB | `hardware/releases/rev3/jlcpcb/preview/3d/hacking_badge_v3_full_assembly_black.glb` |
| 검정 PCB 3D export 묶음 | `hardware/releases/rev3/jlcpcb/preview/3d/hacking_badge_v3_3d_exports_black.zip` |
| 전체 3D export 묶음 | `hardware/releases/rev3/jlcpcb/preview/3d/hacking_badge_v3_3d_exports.zip` |

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

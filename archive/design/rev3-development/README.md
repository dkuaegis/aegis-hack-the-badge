# Rev.3 Development Archive

현재 생산에 사용하지 않는 Rev.3 개발 중간 산출물입니다.

- `pcb-revisions/`: 날짜와 작업 단계별 PCB 스냅샷
- `autoroute/`: Specctra DSN/SES와 중간 DRC 보고서
- `placement/`: 초기 배치 및 centroid 초안
- `legacy-exports/`: 구형 렌더와 3D 출력
- `legacy-reports/`: 과거 DRC 보고서
- `legacy-schematic/`, `rescue-backup/`: KiCad 구조 복구 자료
- `kicad-history/`: KiCad 내부 history의 마지막 작업 트리
- `kicad-history.bundle`: 중첩 저장소를 제거하기 전에 보존한 전체 Git 이력

이력 복원 예시:

```sh
git clone kicad-history.bundle restored-kicad-history
```

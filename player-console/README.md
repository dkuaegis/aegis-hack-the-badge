# Hack The Badge Player USB Console

브라우저의 Web Serial API로 플레이어 PC에 연결된 USB CDC 배지와 직접
통신하는 정적 웹 콘솔입니다. 컨테이너는 HTML/CSS/JavaScript만 제공하며,
USB 장치와의 통신은 웹 서버나 컨테이너를 거치지 않습니다.

관리자 브릿지와 별도 이미지로 구성되어 BLE, 관리자 키, 관리자 HTTP API,
문제 편집, 상태 초기화와 재부팅 기능을 포함하지 않습니다.

## 실행

```bash
cd player-console
docker compose up --build -d
```

플레이어 PC의 데스크톱 Chrome 계열 브라우저에서 다음 주소를 엽니다.

```text
http://localhost:8081
```

`CONNECT USB`를 누르고 배지의 Serial 포트를 선택하면 115200 baud, 8-N-1로
연결됩니다. USB 장치는 컨테이너에 전달하지 않아도 됩니다.

## 플레이어 빠른 시작

1. 배지를 USB로 연결합니다.
2. `CONNECT USB`를 누릅니다.
3. 배지 Serial 포트를 선택합니다.
4. `aegis` 또는 `1`~`4`를 입력합니다.
5. 문제의 안내에 따라 명령 또는 FLAG를 입력합니다.

개편된 4개 Serial Mission은 단순 FLAG 제출만으로 구성되지 않고,
문제 내부 명령을 탐색하는 대화형 흐름을 포함합니다. Serial 출력은
한국어이며 OLED 힌트는 영문 ASCII로 표시됩니다. 입력창의
`COMMAND OR FLAG`에 현재 문제가 안내한 값을 입력하세요.

종료:

```bash
docker compose down
```

## 행사 서버에 배포

Web Serial은 보안 컨텍스트에서만 동작합니다. `localhost`는 로컬 개발용
보안 컨텍스트로 인정되지만, 다른 PC가 행사 서버의 IP나 도메인으로 접속할
때는 앞단 리버스 프록시에서 HTTPS를 적용해야 합니다. HTTPS 페이지를 연
각 플레이어의 브라우저가 그 플레이어 PC에 꽂힌 USB 배지에 직접 연결합니다.

지원하지 않는 브라우저나 HTTP 원격 주소에서는 연결 버튼이 비활성화되고
원인이 화면에 표시됩니다. iframe에 삽입하지 말고 최상위 페이지로 여세요.

### 동시 접속과 Cloudflare Tunnel

nginx는 CPU 수만큼 worker를 실행하고 worker당 연결 4,096개,
컨테이너 파일 디스크립터 한도 65,535개를 사용합니다. 실제 수용량은
서버 CPU·메모리·네트워크와 Tunnel 처리량에 따라 달라집니다.
유휴 연결은 15초 후 정리하며 접근 로그는 버퍼링하고 회전해 디스크 사용을 제한합니다.

HTML은 매번 재검증하며 JS/CSS/SVG는 1시간 캐시합니다. 이미지 빌드 시
자산 URL에 내용 해시를 붙여 새 배포가 이전 캐시를 사용하지 않도록 합니다.
모든 파일은 미리 gzip 압축해 요청마다 압축하는 CPU 비용을 줄입니다.
Cloudflare에서는 기존 Tunnel이 `http://localhost:8081`을 계속 바라보게 하고,
HTML에 `Cache Everything` 또는 강제 Edge TTL을 적용하지 마세요.
지원하는 정적 자산은 Cloudflare 기본 캐시 정책으로도 캐시할 수 있습니다.

배포와 HTTP 검증:

```bash
git pull --ff-only
docker compose -f player-console/compose.yaml up --build -d --wait
python3 player-console/test_http.py
```

테스트 환경에서 부하를 확인하려면 ApacheBench로 실행합니다.
아래 수치는 보장 용량이 아닌 검증용 요청 수입니다.

```bash
ab -n 10000 -c 200 -k -H 'Accept-Encoding: gzip' http://127.0.0.1:8081/
```

정상 결과는 Failed requests와 Non-2xx responses가 모두 0입니다.
콘솔을 연 뒤의 USB 입출력은 서버 접속 없이 계속 동작합니다.
긴 ASCII art는 터미널의 가로 스크롤로 원형을 유지합니다.

## 시리얼 회귀 검증

Node.js 22 이상에서 별도 패키지 설치 없이 실행합니다.

```bash
node --test player-console/app.test.mjs
```

저장소 루트에서 실행하며, 모의 시리얼 스트림으로 수신 대기 중 해제,
정상 종료, 전송 중 해제, USB 분리, 재연결, 읽기·쓰기 오류,
UTF-8 분할 수신, 대량 출력의 버퍼 제한을 확인합니다.
실제 배지와 Chrome에서 장시간 사용 후 해제·새로고침도 확인하세요.

## 구조 및 권한 경계

```text
player browser ── Web Serial ── USB CDC badge
       │
       └── HTTPS/localhost ── static nginx container
```

- 서버로 Serial 데이터 전송 없음
- 관리자 브릿지 API 호출 없음
- BLE 관리자 인증 정보 없음
- 브라우저의 사용자 장치 선택 승인 필수

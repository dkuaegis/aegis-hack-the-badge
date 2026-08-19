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

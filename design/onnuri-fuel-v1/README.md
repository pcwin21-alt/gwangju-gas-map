# 온누리 주유소 지도 디자인 체계 v1

~~32개~~ **정책 안내 S06을 추가한 33개 구성요소**·9개 상태/변형의 **검토용 원본**이다. 실제 토스 출시 버전은 바꾸지 않았다.

- `tokens.css`: 색·서체·크기·간격·반경·그림자.
- `components.css`: 독립 재사용 컴포넌트와 상태.
- `prototype.css`, `prototype.js`: 현재 고정 지도에 적용하는 검토 전용 연결부.
- `inventory.json`: 전체 요소 ID와 계약, 실제 갤러리의 같은 ID 연결.
- `fonts/`: 원본 Pretendard Regular/Bold와 OFL 라이선스. 폰트 바이너리 수정 없음.

생성: 저장소 루트에서 `python -X utf8 scripts/build_design_review.py`.

결과: `output/design-system-20261104/site/index.html`(전체 요소), `app/`(실제 지도), `screens.html`(대표 화면). HTTP 미리보기로 확인한다. 지도 SDK는 기존 등록 도메인 localhost:8080에서 실행한다.

디자인 결정·레퍼런스·검수와 배포 경계는 [디자인 정본](../../docs/MOBILE_DESIGN_SYSTEM_20261104.md)에 있다. 이 폴더는 자동 배포 연결점이 아니며 자체로 가맹점 조회·새 로그 수집·콘솔 작업을 실행하지 않는다.

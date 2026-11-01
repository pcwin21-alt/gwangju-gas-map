# 지도 핀 상세창 깜빡임 수정 — 2026-11-02

## 요청과 범위

사이드 채팅에서 사용자가 웹 지도의 핀을 클릭하면 주유소 정보 대신 깜빡임만 보인다고 제보했다. 요청은 오류 수정 및 채팅 밖의 영속적인 수정 기록이다. 가맹점 조사·수집과 관련된 메인 채팅의 진행 중 변경은 이번 작업 범위가 아니다.

- 과업: 지도 핀 선택 → 해당 주유소명·주소·결제 정보·길찾기 표시 유지.
- 수락 조건: 같은 핀의 중복 이벤트가 창을 닫거나 다시 만들지 않는다. 다른 핀은 한 번 교체된다. 터치 시작만으로 창이 사라지지 않는다. 실제 지도 드래그, 닫기 버튼, Escape로 닫을 수 있다. 핀 선택이 지도 중심·확대 수준을 바꾸지 않는다.
- 작업 폴더: `C:\Users\unw\OneDrive\Documents\Playground\tmp\gwangju-gas-map-pin-fix-20261102`
- 기준 커밋: `ebe1b6eeaec3d45fa8c1ef6d78cbca96b0b3578c`
- 기존 작업 폴더의 소스·git 상태를 보존하기 위해 별도 로컬 복제본에서 수정했다.

## 원인과 재현 근거

배포본에서 일반 마우스 단일 클릭으로 정보가 열리는 경우를 확인했다. 따라서 모든 기기에서 단일 클릭이 항상 실패한다고 단정하지 않는다.

코드 기반 회귀 시험에서는 아래 실패를 재현했다.

1. 같은 마커의 SDK click이 연속 전달되면, 기존 핸들러는 첫 이벤트로 연 창을 두 번째 이벤트에서 닫는다.
2. `.map-area`의 capture `pointerdown`·`touchstart`가 핀 선택 여부와 관계없이 상세창을 지운다. 선택 직후 다른 호환 이벤트가 전달되면 창이 제거·재삽입된다.
3. 다른 핀으로 바꾼 뒤 동일 이벤트가 재전달되어도 새 상세창이 닫힌다.

수정 전 신규 회귀 시험 5개 중 4개 실패, 1개 통과. 실제 사용자의 정확한 장치 이벤트 순서는 미수집이며, 위 이벤트 순서를 브라우저 실기 재현과 혼동하지 않는다.

## 수정

- `showStationOverlay`: 이미 선택한 핀이면 즉시 반환한다. DOM 재삽입·포커스 재설정을 하지 않아 스크롤과 읽기 맥락도 보존한다.
- 마커 click: 닫기/열기 토글을 제거하고 선택 함수만 호출한다. 다른 주유소의 이전 창 정리는 기존 선택 함수가 한 번 수행한다.
- pointerdown/touchstart: 예약된 지도 자동 맞춤 취소는 유지하고, 상세창 자동 닫기는 제거한다.
- Kakao 지도 dragstart: 실제 드래그가 시작될 때 상세창을 닫는다. 카드 내부 스크롤은 지도에 전파되지 않는 기존 처리를 유지한다.
- wheel·닫기 버튼·Escape·필터에서 선택 주유소 제외 시 닫기는 유지한다.
- 지점 데이터, 가격, 결제 확인 상태, 가맹점 수집 방식, 서체·색상·배치는 변경하지 않는다.

## 실행 계약 및 하네스 선택

- 입력: 사용자 제보, 현재 배포본, `output/map.html`, 기존 테스트.
- 행동: 재현 시험 추가 → 수정 전 실패 확인 → 이벤트 처리 수정 → 관련 자동 시험 및 브라우저 조작 → 수정만 커밋·배포.
- 출력: 지도 수정, `tests/station-pin.test.js`, 본 기록, 검증 및 배포 증거.
- always: canonical identity harness의 AGENTS/Skill Router/Brain, 최소 프로젝트 계약(본문), Project Execution, Global Completion Gate.
- active: `toss-ux-principles`(핀 선택·포커스·지도 맥락 보존), `codex-delivery-loop`(격리 작업·시험·브라우저 확인·기록), Software and Website UX Gate.
- reference: KRDS typography skill(기존 정보 계층·16px 본문·44px 닫기 조작 보존; 타이포그래피 변경 없음), Computer Use(브라우저 검증).
- excluded: 신규 프로젝트 기획, 가맹점 수집·외부 자료 조사, 문체·발표·콘텐츠 관련 스킬. 기존 기능의 이벤트 오류 수정에 불필요.
- drift: harness index의 workspace_root는 이전 루트를 가리킨다. 현재 사용자가 지정한 `identity_harness` 실제 파일을 정본으로 적용했다. CLAUDE.md의 예전 수집/API 설명은 이번 UI 수정에 사용하지 않는다.

## 검증 및 배포

- `node --test tests/station-pin.test.js tests/station-details.test.js tests/map-viewport.test.js tests/input-ux.test.js`: 관련 20개 통과.
- `node --test tests/*.test.js`: 91개 통과.
- `python -m unittest discover -s tests -p 'test_*.py'`: 104개 통과. 기존 Shapely deprecation warning 1건; 실패 없음.
- `python scripts/prepare_site.py`, `git diff --check`: 성공.
- 신규 회귀 시험: 중복 SDK click, touch/pointer 혼합 순서, 다른 핀 전환, 실제 드래그 닫기, 제보 모드에서 선택 무시.
- 로컬 `127.0.0.1:4197` 및 `localhost:4197`에서는 Kakao SDK가 로드되지 않아 주소 목록 fallback을 확인했다. 이를 지도 핀의 브라우저 검증으로 보고하지 않는다.
- 실제 배포 지도 브라우저 검증과 배포 실행 결과: 배포 후 본 문서에 추가 예정.
- 실제 휴대전화 하드웨어의 터치 순서는 미검증. 브라우저 크기 검증·모의 이벤트 시험과 구분한다.

메인 채팅 인수인계: 이 수정은 가맹점 수집 작업과 별도다. 원래 작업 폴더에 덮어쓰거나 메인 작업의 미커밋 파일을 함께 커밋하지 않는다. 이후 메인 작업을 배포할 때 GitHub main의 본 수정 커밋을 먼저 반영해야 예전 토글 동작으로 되돌아가지 않는다.

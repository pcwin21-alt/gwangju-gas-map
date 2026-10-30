# 모바일 입력·지도 조작 수정

요청: 입력하려면 키보드가 안 열리고 지도 조작 때 열리는 등 모바일 사용성 오류 조사·수정.

## 원인과 변경
- 관찰한 코드: 복사 시 편집 가능한 숨겨진 textarea를 focus/select. 읽기 전용 + inputmode none으로 바꿔 편집 키보드 유발 경로 제거.
- 지도 조작 시 기존 입력 focus가 남음. 지도 pointerdown에서 편집 focus만 해제하고 기본 이벤트는 취소하지 않음. 지도 위 입력창 자체는 제외.
- 버튼/패널을 닫아도 입력 focus가 남는 경로: 명시적인 비입력 행동 때 blur, 접힌 경유 패널 내부 입력 blur. 검색 지우기는 이어서 편집하는 행동이므로 유지. 경로 수정처럼 입력 목적이 명확한 기존 동기 focus는 유지.
- 복사 버튼의 mousedown 전용 처리를 click으로 통합해 터치/키보드 지원. 길찾기 링크의 touchend 중복 실행 제거하여 스크롤 끝에 길찾기가 실행되는 경로 제거.
- 경유 검색/제보 주소 검색의 한글 조합 Enter를 제출로 취급하지 않음(isComposing/keyCode 229). 검색 입력에 enterkeyhint, 주유소 검색 Enter는 편집 종료.
- viewport resize에서 focus를 이동하지 않음. visualViewport 높이를 앱에 적용하고 pinch zoom 중에는 재계산하지 않음. 키보드가 공간을 차지할 때 경유 입력 영역을 스크롤 가능하게 제한. 모바일 입력은 16px 이상/44px 이상.

## 계약·라우팅
- 이전 UI 작업 계약과 canonical harness Project Execution / Brain / Source / Eval, codex-delivery-loop / computer-use / KRDS 최소 조합을 계속 적용.
- 수락: 입력 직접 탭 focus 유지, 지도 조작 focus 해제·기본 제스처 유지, 한글 조합 중 미제출, 버튼/패널 전환에 숨은 입력 focus 없음, 화면 축소 시 입력·검색 조작 가능, 기존 필터·경유 동작 유지.
- 범위: 기존 지도 입력/검색/복사/경유/주소/댓글 필드. 데이터 변경·위치 전송 없음.
- Node 31개/Python 100개 통과. 신규 단위 검사는 지도 제스처 blur, 지도 내 입력 예외, 버튼 편집 종료, visualViewport/핀치 보존, 접힌 패널 focus 해제, 한글 조합 Enter 미제출.
- 실제 iOS/Android OS 키보드 재현은 이 PC 브라우저로 확인할 수 없음. 원인 코드를 고치고 브라우저 DOM focus/작은 화면/실제 검색 경로를 확인한다. 사용자의 실제 기기 증상이 전부 해소됐다고 단정하지 않는다.
- 배포 bcd2564 검수: 390×844 주유소 입력 탭 focus 확인, 지도 드래그 후 BODY로 focus 해제, 목적지 입력/Enter 실제 검색 결과 확인, 출발지 직접 탭 focus 확인.
- 390×420 축소 검수 중 출발지 input이 22px 폭으로 렌더되는 기존 CSS 충돌 확인. visual-refresh의 flex용 width:0을 새 grid 배치에서 width:100%로 덮어씀. viewport/focus 변경 후 활성 입력이 내부 스크롤 영역에 보이도록 보정.
- 주유소 목록 선택 뒤 상세창이 지도 위쪽으로 잘리고 목록이 상세를 가리는 문제 확인. 선택 시 목록을 접고 상세창을 지도 안쪽으로 이동, 상세 내용은 지도 높이 안에서 스크롤하도록 보완.

## 사용자 환경 답변 후 보완
- 이전 질문의 2번=안드로이드 Chrome, 3번=카카오톡·네이버 등의 앱 내 브라우저. 사용자가 두 환경 모두라고 응답. iPhone Safari 사용으로 해석하지 않음.
- 같은 canonical Project Execution/Brain/Source/Eval 및 delivery-loop/KRDS 계약을 유지하는 후속 입력 호환성 수정. 새로운 데이터·가격·가맹점 변경 제외. 갱신된 origin/main 가맹점 기록을 먼저 fast-forward하여 보존.
- 회전 지도에 별도로 있던 pointer 전용 blur를 제거하고 지도 영역 전체의 공통 pointerdown+touchstart 처리로 통합. PointerEvent가 선언된 환경에서도 touch fallback 사용, 입력 요소 자체 터치는 그대로 통과. 기본 제스처 preventDefault 없음.
- visualViewport만 축소되는 경우와 window.innerHeight까지 함께 축소되는 경우를 모두 평상시 높이와 비교. readonly clipboard textarea는 편집 중으로 간주하지 않음. viewport scroll/pan 때 입력 영역의 실제 가시 범위를 기준으로 내부 스크롤만 보정하며 focus를 강제하지 않음.
- 제보/댓글 패널은 키보드가 열린 가시 높이 내로 제한하고 내부 스크롤 허용.
- 근거: https://developer.chrome.com/blog/viewport-resize-behavior (Android Chrome/WebView의 viewport 동작 차이), https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport (height/offsetTop/scroll).
- 추가 검사: touch fallback, 두 viewport 동시 축소, readonly 제외, viewport pan 시 입력 가시 범위. 관련 Node 13개/전체 CI 150개 통과. 공개 배포에서 검색 입력 직접 focus → 회전 canvas 터치 시 text focus 해제. 390×420 축소 시 댓글 입력 유지, 패널 top24/bottom420, 입력 bottom408 확인. 증거 Playground/output/onnuri-input-shrunken-20261030.jpg. 안드로이드 실제 OS 키보드와 카카오톡/네이버 앱의 WebView 재현은 이 Windows 브라우저로 검증 불가.

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

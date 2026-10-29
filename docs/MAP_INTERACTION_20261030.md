# 지도 조작

## 요청과 수락
- 요청: 모바일 두 손가락 회전 및 지도 조작 편의 개선.
- 산출물: 기존 지도 위 회전 모드 진입/N 북쪽 정렬, 확대·축소, 지도 크게 보기/Escape 복귀.
- 기존 가맹점 데이터·필터·상세·경유·현재위치 연결 유지. 모바일 제스처는 입력창 focus를 만들지 않음.
- canonical identity_harness 기존 Router/Project Execution/Brain/Source/Eval 및 codex-delivery-loop/computer-use/KRDS 최소 계약을 후속 적용. 새 제품 기획·데이터 조사·다중 에이전트 제외.

## 근거와 선택
- 카카오 공식 답변: https://devtalk.kakao.com/t/topic/135421 (2024, 현 JS SDK의 회전 API 없음에 대한 공식 답변). 현재 저장소는 Kakao JS SDK.
- MapLibre 공식: https://maplibre.org/maplibre-gl-js/docs/API/classes/TwoFingersTouchZoomRotateHandler/ 두 손가락 확대·회전 지원.
- 타일 제공 설정: https://openfreemap.org/quick_start/ 의 liberty 벡터 스타일. 기본 자동 저작권 표기 유지.
- 기존 카카오 지도를 기본 유지. 이용자가 회전을 누를 때 MapLibre GL JS 5.12.0(정식 npm 패키지)과 OpenFreeMap만 로드. 카카오 타일 DOM 자체를 회전시키지 않음. 로딩/연결 실패 시 원래 지도 유지.
- assets/maplibre-gl-5.12.0.js/css와 maplibre-LICENSE.txt는 npm registry 배포본에서 원형 복사. 웹 번들 약 1MB(압축 전). 별도 계정/결제/API 키 추가 없음.
- 전환해도 원래 지도 카메라와 필터 상태를 동기화. 돌아가기 동작과 자동 예외 복귀(지도 위치 제보·가격 순위)는 기존 카카오 동작을 유지.
- 회전 지도 상세는 별도 고정 영역에 기존 상세 DOM을 사용. MapLibre 마커는 현재 표시 조건의 가맹점만 포함.
- 크게 보기는 브라우저의 OS 전체화면 API 대신 앱의 검색·메뉴 영역을 접는 방식. iOS/인앱 브라우저에서도 같은 동작. Escape 복귀, 닫기 버튼 유지.
- 터치 기울기 비활성화(평면 지도), 핀치 확대와 회전 활성화. 감소 모션 설정 반영.

## 검증
- 기존 Node 31개/Python 100개 통과. JS 구문 및 사이트 생성 통과.
- 실제 터치스크린의 두 손가락 제스처는 현재 PC 도구에서 재현할 수 없음. 공급자 지원과 지도 핸들러 활성 설정을 확인하고, 실제 브라우저에서 회전/북쪽 복원/필터/상세/화면 확대를 검수한다.
- 회전 모드 기본 로드/실패 복구/조건 동기화/화면 확대 복귀의 신규 단위 4개 추가 통과.
- 390×844 배포 검수에서 지도 크게 보기/Escape 복귀, 회전 모드 로딩과 저작권 표기 확인. 지연 로드된 공급자 CSS가 지도 컨테이너 position을 덮어쓰는 충돌을 발견하여 ID 선택자로 고정.
- 상태: 구현 및 자동 검사 완료, 최종 렌더와 조작 검수 진행.

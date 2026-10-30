# 기존 카카오 지도 하나로 정리

- 사용자 정정: 회전을 위해 별도 지도를 만들라는 뜻이 아니었으며, 기존 지도에서 안 되면 회전을 제거해도 됨. 빈 2번 항목은 임의 구현하지 않음.
- 계약/라우팅: 기존 canonical Project Execution/Brain/Source/Eval Global·UX, codex-delivery-loop/computer-use/KRDS 유지. 입력=기존 지도/기능과 사용자 정정, 행동=별도 렌더러/전환/회전 제거, 수락=카카오 단일 지도에서 확대·전체 보기·주유소 상세·경로/번호·플로팅 창 유지. 데이터/가격 갱신·새 지도/SDK 도입 제외.
- 근거: Kakao 공식 답변 https://devtalk.kakao.com/t/topic/135421 는 JS SDK 회전 미제공, Android/iOS native SDK와 구분. 최신 Web API 문서 https://apis.map.kakao.com/web/documentation/ 에서도 회전 메서드 확인되지 않음.
- 제거: 회전/N 버튼, 원래 지도 복귀 버튼, 두 번째 지도와 별도 상세 컨테이너, 야간 모드의 지도 자동 전환, 벡터 렌더러/타일/폰트 로드, 관련 라이브러리/CSS/license(라이브러리 함께 제거).
- 유지: 카카오 기본 지도/핀/검색·현재 위치·확대·축소·크게 보기/Escape·실제 도로 경로·번호 추천·플로팅 경유 창/배경 불투명도. 기본 지도에서 추천 상세를 바꿀 때 이전 overlay를 정리. SDK 실패 때 경유 launcher 숨김.
- 다크/화이트 UI 팔레트는 유지. 카카오 지도 타일은 기본 색상 유지하며 별도 야간 지도나 CSS 색 반전을 추가하지 않음. 이 결정은 이전 THEME/MAP_INTERACTION/ROUTE_MAP 문서의 회전·별도 야간 지도 관련 설명을 대체.
- 검사: Node 51 통과. 단일 지도/회전 전환 없음, zoom bounds, 전체 보기/Escape, 경로 활성 중 필터·핀 분리/복원, SDK 실패 검증. 전체 CI/공개 화면 후속 확인 중.

/* Local UI translations. Merchant names, addresses, inputs and route data stay intact. */
(function(root) {
  'use strict';
  const messages = {
    '화면 테마':'Appearance','기기 설정':'System','밝게':'Light','어둡게':'Dark',
    '주유소 상세 닫기':'Close station details',
    '지도 보기':'Map view',
    '지도 크게 보기':'Expand map','지도 작게 보기':'Restore map','지도 확대':'Zoom in','지도 축소':'Zoom out','지도 확대 축소':'Map zoom',
    '내 위치로 이동':'Go to my location','위치 찾는 중':'Finding location',
    '에서 결제수단·유종·시군구를 고릅니다. 선택한 조건은 접어도 표시됩니다.':'Choose payment, fuel and district. Active filters stay visible when collapsed.',
    '에서 목적지를 검색하고 선택하세요. 출발지·조건은 필요할 때 변경할 수 있습니다.':'Search for and select a destination. Change the start and options when needed.',
    '에서 가격 순위·언어·사용법·제보 등 보조 기능을 엽니다.':'Open prices, language, help, reporting and other tools.',
    '필터':'Filters','검색 필터':'Search filters','조건 초기화':'Clear filters','시·군·구':'District',
    '어디로 가시나요?':'Where are you going?','목적지 검색':'Search destination',
    '출발지·조건 변경':'Change start / options','모든 결제수단':'All payments','모든 유종':'All fuels',
    '출발지 선택 필요':'Select a start','경로 계산 안내':'About route estimates',
    '경유 주유소를 찾으면 추가 이동시간을 비교합니다.':'Find stations to compare detour times.',
    '검색·지역·내 위치를 앞에 두고, 세부 조건은 필터로 모았습니다. 경유 찾기는 목적지부터 입력하고 출발지와 조건은 필요할 때 변경합니다.':'Search, region and location stay up front; detailed options are under Filters. Route search starts with the destination, with start and options available when needed.',
    '전국 온누리 주유소 지도':'Onnuri fuel stations across Korea',
    '상생카드와 온누리 공식 검색 결과를 표시합니다. 현행 검색과 대조되지 않은 곳은 과거 기록으로 구분합니다. 유가와 가맹점 확인일은 별개입니다.':'Sangsaeng and Onnuri use official search results. Unmatched older records are marked historical. Price and merchant check dates are separate.',
    '유가: 하루 1회 조회 · 가맹점: 매일 오전 6시 30분 확인':'Prices: daily lookup · Merchants: daily at 06:30 KST',
    '공식 검색·품목 자료로 확인한 주유소입니다. 전국 모든 가맹점이 포함된 것은 아닙니다.':'Stations are checked against official search and product records. Coverage is not exhaustive.',
    '온누리 공식 검색 ↗':'Search official Onnuri merchants ↗',
    '최근 조회 실패, 이전 자료 유지':'Latest lookup failed; previous data retained',
    '전국 온누리 · 광주상생카드 가맹점':'National Onnuri · Gwangju Sangsaeng merchants',
    '시·도':'Province', '온누리 유형':'Onnuri type','유종':'Fuel','전국':'All regions',
    '디지털':'Digital','지류':'Paper','지류·디지털':'Paper · Digital','휘발유·경유':'Petrol · Diesel','전체 시·군·구':'All districts',
    '조건에 맞는 주유소':'Filtered stations','선택한 지역·검색어·필터에 따른 목록':'Matches your selected region, search and filters','더 보기':'Show more','공식 가맹점 자료':'Official merchant data',
    '조건에 맞는 확인된 등록이 없습니다. 지역이나 결제 유형을 바꿔보세요.':'No verified listings match. Try another region or payment type.',
    '공식 온누리 자료의 후보 중 상세주소 또는 자동차 주유 업종 확인이 필요한 기록입니다. 지도와 길찾기에서는 제외합니다.':'These official-file candidates still need a street address or vehicle-fueling category check. They are excluded from the map and directions.',

    '(구)광주광역시 주유소 지도':'Gas stations in former Gwangju',
    '주유소 지도 로고':'Gas station map logo',
    '상생카드·온누리 할인 가맹점 모음':'Sangsaeng Card & Onnuri discount merchants',
    '오늘':'Today','· 전체':'· Total','더보기':'More','사용법 안내':'Help',
    '✉ 오류·누락 신고':'✉ Report an issue','오류·누락 신고 / 문의':'Report an issue / Contact',
    '☕ 커피 사주기':'☕ Buy me a coffee','이 지도가 도움이 됐다면':'If this map helped you,',
    '개발자에게 커피 한 잔 선물해주세요!':'buy the developer a coffee!',
    '카카오페이 QR코드':'Kakao Pay QR code','카카오페이 앱으로 QR을 스캔하세요':'Scan with the Kakao Pay app',
    '닫기':'Close','📖 사용 안내':'📖 Help','이 지도는?':'About this map',
    '광주광역시에서':'In former Gwangju,','광주상생카드':'Gwangju Sangsaeng Card','또는':'or',
    '온누리상품권':'Onnuri vouchers','으로 결제 가능한 주유소를 한눈에 볼 수 있는 지도입니다.':'find gas stations that accept these payment methods.',
    '상생카드만':'Sangsaeng only','온누리만':'Onnuri only','둘 다 가능':'Both accepted',
    '주요 기능':'Features','마커 클릭':'Tap a marker',
    '→ 주유소 이름·주소, 결제 가능 수단, 현재 유가(휘발유·경유·LPG) 확인':'→ See the station name, address, payment methods and fuel prices.',
    '검색창':'Search','에 주유소명이나 주소를 입력하면 해당 위치로 이동합니다.':'Enter a station name or address to show matching stations.',
    '상생카드 / 온누리 / 전체':'Sangsaeng / Onnuri / All',
    '버튼으로 원하는 결제수단의 주유소만 볼 수 있습니다.':'Filter stations by the payment method you use.',
    '구 필터':'District filter','(광산구·남구·동구·북구·서구)로 원하는 지역만 볼 수 있습니다.':'Choose Gwangsan, Nam, Dong, Buk or Seo district.',
    '가격 순위':'Lowest prices','→ 현재 보이는 주유소 중 휘발유·경유·LPG 가격 TOP 5를 확인합니다.':'→ See the top 5 lowest prices among the filtered stations.',
    '📍 내 위치':'📍 My location','내 위치':'My location',
    '→ 현재 위치를 지도 중심으로 이동합니다. (브라우저 위치 권한 필요)':'→ Center the map on your location. Browser location permission is required.',
    '길찾기':'Directions','→ 주유소 팝업에서 카카오맵 또는 네이버지도를 바로 엽니다.':'→ Open KakaoMap or Naver Map from a station popup.',
    '주변 내보내기':'Export nearby stations','↗ 주변 내보내기':'↗ Export nearby stations',
    '→ 내 위치 기준 가까운 주유소 링크 목록을 복사합니다.':'→ Copy links to stations near your location.',
    '↺ 초기화':'↺ Reset','→ 필터·검색·지도 위치를 한 번에 원래대로 되돌립니다.':'→ Reset filters, search and map view.',
    '누락·오류 제보':'Report an issue','지도에 없는 주유소, 잘못된 정보가 있다면':'Found a missing station or incorrect information?',
    '+ 제보':'+ Report','버튼을 눌러 알려주세요. 지도에서 위치를 직접 찍거나 주소를 입력하고, 사진도 첨부할 수 있습니다.':'Use Report to choose a map location or enter an address. You can also attach a photo.',
    '이메일로도 신고 가능 →':'You can also email →','데이터 출처':'Data sources',
    '상생카드: 광주시 가맹점 조회 / 온누리: 소상공인시장진흥공단 공식 파일·기존 위치 기록 / 유가: 오피넷(한국석유공사)':'Sangsaeng: official city merchant lookup / Onnuri: official SEMAS file and existing location records / Fuel prices: Opinet (KNOC)',
    '상생카드는 공식 조회 결과, 온누리는 연간 공식 자료와 대조한 기록을 표시합니다. 온누리 자료 기준일과 매칭 미완료 여부는 각 주유소에서 확인하세요. 유가 갱신일과 가맹점 자료 기준일은 다릅니다.':'Sangsaeng uses official lookup results. Onnuri records are matched against an annual official file. Check each station for the source date and unmatched status. Fuel price dates differ from merchant source dates.',
    '공유 안내':'Sharing','이 지도는':'This map may be','주변에 자유롭게 공유':'freely shared',
    '하셔도 됩니다. 다만 트래픽이 몰릴 경우 서버가 불안정해질 수 있으니 양해 부탁드립니다. 관심과 성원이 많다면 서버를 확대해 보겠습니다.':'with others. High traffic may affect availability. More capacity may be added as usage grows.',
    '문의·건의사항 →':'Questions / Suggestions →',
    '주유소명 · 주소 검색...':'Search station or address…','주유소명 또는 주소 검색':'Search station name or address','지우기':'Clear',
    '검색 결과 없음':'No matching stations','전체':'All','상생카드':'Sangsaeng','온누리':'Onnuri','둘 다':'Both',
    '지역 선택':'Choose a district','전체 지역':'All districts','전체 구':'All districts',
    '광산구':'Gwangsan-gu','남구':'Nam-gu','동구':'Dong-gu','북구':'Buk-gu','서구':'Seo-gu',
    '더보기 닫기':'Close menu','지도 도구':'Map tools','업데이트 내역':'Updates','업데이트 내역 닫기':'Close updates',
    '☕ 개발자에게 커피사주기':'☕ Buy the developer a coffee','💬 반응 남기기':'💬 Leave feedback','현재 데이터':'Current data',
    '유가: 3시간마다 갱신 · 가맹점: 매일 오전 6시 30분 확인':'Fuel prices: every 3 hours · Merchants: daily at 06:30 KST',
    '온누리는 연간 공식 자료입니다. 매칭되지 않은 곳은 과거 기록으로 표시합니다.':'Onnuri uses an annual official file. Unmatched stations retain historical records.',
    '온누리 공식 자료 확인 ↗':'View official Onnuri data ↗',
    '경유 주유소 찾기':'Find a station on your route','목적지까지 추가 이동시간 비교':'Compare detours to your destination',
    '열기 ＋':'Open ＋','접기 −':'Hide −','출발지':'Start','최종 목적지':'Destination','목적지':'Destination',
    '비워두면 내 위치':'Leave blank for my location','검색':'Search','장소명 또는 도로명주소':'Place name or street address',
    '추가 이동시간 비교':'Compare detours','결제수단':'Payment','결제 수단':'Payment methods','연료':'Fuel',
    '휘발유·경유 주유소':'Petrol / diesel','LPG 충전소':'LPG stations','온누리 종류':'Onnuri type','디지털':'Digital','지류':'Paper',
    '목적지를 검색해 선택하세요.':'Search for and select a destination.',
    '도로 경로 기반 시험 기능입니다. 실시간 교통·주유시간·주유소 진입 방향은 반영하지 않으며 내비 경로와 다를 수 있습니다. 비교를 누르면 출발지·목적지·후보 좌표가 OSRM 경로 서비스에 전달됩니다.':'Trial road estimates exclude live traffic, refueling time and station entrance direction, and may differ from navigation apps. Compare sends start, destination and candidate coordinates to the OSRM routing service.',
    '경로 수정':'Edit route','주변 주유소 내보내기':'Export nearby stations',
    '네이버지도·카카오맵 즐겨찾기 일괄 저장용 공개 API는 없어, 가까운 주유소 링크 목록으로 대신 내보냅니다.':'Bulk bookmarks are not supported by the map apps. Export a list of nearby station links instead.',
    '반경':'Radius','가까운 순':'Nearest first','개수':'Limit','카카오맵':'KakaoMap','네이버지도':'Naver Map',
    '내 위치를 확인하면 가까운 주유소가 표시됩니다.':'Use your location to see nearby stations.',
    '📍 새 주유소 제보':'📍 Report a station','위치 지정':'Choose location','위치가 설정되지 않았습니다':'No location selected',
    '주소 검색 (예: 광주광역시 북구 ...)':'Search an address (e.g. Gwangju Buk-gu…)','📍 지도를 클릭해 위치 지정':'📍 Choose a location on the map',
    '주유소 정보':'Station details','주유소명 *':'Station name *','기타 (선택)':'Notes (optional)',
    '가격, 영업시간, 특이사항 등 자유롭게 적어주세요':'Add prices, opening hours or other details',
    '결제 영수증 사진 (선택)':'Receipt photo (optional)','📎 사진을 클릭해 선택하거나 여기로 드래그':'📎 Choose or drag a photo here',
    '영수증 미리보기':'Receipt preview','📨 제보 등록하기':'📨 Submit report','제보 내용은 운영자가 검토 후 지도에 반영됩니다':'Reports are reviewed before being added to the map.',
    '✓ 이메일이 열렸습니다!':'✓ Email opened!','선택하신 사진을 방금 열린 메일에':'Please add the selected photo to the email',
    '직접 첨부':'as an attachment','해 주세요.':'before sending.','(메일 앱 → 첨부파일 아이콘 → 아래 사진 선택)':'(Email app → Attach file → Choose the photo below)',
    '첨부할 사진':'Photo to attach','👑 저렴한 주유소 TOP 5 · 할인 전 기준':'👑 Top 5 lowest prices · Before discount',
    '가격 미확인':'Price unverified','휘발유':'Petrol','경유':'Diesel','결과 보기':'Show results','📍 제보할 주유소 위치를 지도에서 클릭하세요':'📍 Tap the station location on the map','취소':'Cancel',
    '이 지도, 어떠셨나요?':'How was this map?','초기 버전 운영 중':'Early version','— 서버가 충분하지 않습니다.':'— Server capacity is limited.',
    '이용자가 많아지면 기능을 확장할 예정이에요.':'More features may be added as usage grows.',
    '지도가 도움이 되셨다면, 아래 버튼을 클릭해주세요!':'Tell us what you think below.',
    '도움됐어요':'Helpful','더 많이 필요해요':'I want more','주변에 알릴게요':'I will share it','아쉬워요':'Needs improvement',
    '✏️ 반응 없이 댓글만 남기기':'✏️ Leave a comment only','💬 한 마디 남겨주세요':'💬 Leave a comment',
    '닉네임 (미입력 시 익명)':'Nickname (optional)','비밀번호 (삭제 시 사용)':'Password (to delete your comment)',
    '자유롭게 작성해 주세요...':'Write your comment…','등록하기':'Post','💬 방문자 댓글':'💬 Comments','불러오는 중...':'Loading…','복사됨':'Copied',
    '할인 전 단가':'Unit price before discount','상생카드 10% 적용 체감가':'Effective price with 10% Sangsaeng discount',
    '내 위치 직선거리':'Straight-line distance from me','내 위치 확인 전':'Location not set',
    '이 주유소 들러서 목적지로':'Via this station to destination','네이버 내비로 경유':'Navigate via station in Naver','카카오맵 경유':'Via station in KakaoMap',
    '추가 이동시간 미계산':'Detour not calculated','종류 미확인':'Type unverified','미확인':'Unverified','최근 미확인':'Not recently verified',
    '📍 위치 찾는 중...':'📍 Finding location…','전송 중...':'Sending…','✅ 제보 완료!':'✅ Report submitted!',
    '주유소를 선택하거나 추가 이동시간을 비교하세요.':'Select a station or compare detours.',
    '검색할 장소 또는 주소를 입력하세요.':'Enter a place name or address.','장소 검색 중…':'Searching places…',
    '장소를 찾지 못했습니다. 도로명주소나 다른 이름으로 검색하세요.':'No place found. Try a street address or another name.',
    '검색 결과에서 출발지를 선택하세요.':'Select a start from the search results.','검색 결과에서 목적지를 선택하세요.':'Select a destination from the search results.',
    '출발지 검색 결과를 먼저 선택하세요.':'Select a start from the search results first.',
    '이 장소는 상세 좌표 또는 자동차 주유 업종 확인이 필요합니다.':'This place needs verified coordinates or confirmation as a vehicle fuel station.',
    '최종 목적지를 검색해 선택한 뒤 이 주유소를 다시 선택하세요.':'Select a destination, then choose this station again.',
    '출발지를 입력하거나 위치 권한을 허용하세요.':'Enter a start or allow location access.',
    '도로 경로 조회가 지연되고 있습니다. 잠시 후 다시 시도하거나 주유소를 직접 선택하세요.':'Routing is delayed. Try again later or select a station directly.',
    '자동차 경로를 찾지 못했습니다. 출발지·목적지를 확인하세요.':'No driving route found. Check the start and destination.',
    '출발지와 목적지가 너무 가깝습니다.':'The start and destination are too close.',
    '이 결제수단으로 추천할 주유소가 없습니다. 다른 결제수단을 선택하세요.':'No stations found for this payment method. Choose another method.',
    '진입 도로를 확인할 수 있는 후보가 없습니다. 주유소를 직접 선택하세요.':'No candidates with a verified road connection. Select a station directly.',
    '조회가 취소되거나 시간이 초과됐습니다. 다시 비교하거나 주유소를 직접 선택하세요.':'Request canceled or timed out. Compare again or select a station directly.',
    '경로 또는 결제수단을 수정한 뒤 다시 비교하세요.':'Edit the route or payment method, then compare again.',
    '조건이 변경됐습니다. 추가 이동시간을 다시 비교하세요.':'Filters changed. Compare detours again.',
    '네이버 내비 연결은 휴대폰에서 사용하세요. PC에서는 카카오맵 경유 경로를 열 수 있습니다.':'Use Naver navigation on a phone. On desktop, open the KakaoMap route.',
    '모바일 중심으로 디자인을 개편했습니다. 검색·결제 필터·위치·가격 순위를 우선 배치하고, 보조 도구는 더보기로 모았습니다. 지도 위 가림을 줄이고 버튼·입력창·팝업의 크기와 색상을 통일했습니다.':'Redesigned for mobile with search, payment filters, location and price ranking up front. Secondary tools moved to More, with consistent controls and fewer map obstructions.',
    '하단의 예전 버전·날짜·개인 연락처 표시를 제거하고, 오류·누락 신고 및 문의 이메일을 pcwin21@gmail.com으로 통일했습니다.':'Removed the outdated footer and changed the contact email to pcwin21@gmail.com.',
    '모바일의 구별 버튼을 선택형 지역 필터로 줄였습니다. 지역·결제수단·검색 결과를 지도 안에 맞추고, ‘결과 보기’ 버튼과 화면 회전·경유창 전환 시 지도 크기 보정을 추가했습니다.':'Added a compact district selector, automatic result fitting, Show results and map resizing on rotation or route-panel changes.',
    '경유 검색 입구를 눈에 띄는 ‘경유 주유소 찾기’ 버튼으로 바꾸고, 열기·접기 상태를 표시했습니다.':'Made route search more prominent with clear open/closed states.',
    '상단 조회 현황을 업데이트 내역 팝업으로 이동했습니다.':'Moved data status into Updates.',
    '온누리 2026년 7월 31일 기준 공식 자료로 기존 가맹점 100곳을 대조했습니다. 매칭되지 않은 3곳은 최근 미확인으로 유지했습니다.':'Matched 100 existing merchants against the official Onnuri file dated July 31, 2026. Three unmatched records remain not recently verified.',
    '지류·디지털 가맹 여부와 자료 기준일을 주유소 상세창과 경유 후보에 표시합니다.':'Station details and route candidates show paper/digital acceptance and source dates.',
    '온누리 갱신을 공식 파일 조회 방식으로 바꿨습니다. 조회 실패 시 마지막 확인 자료를 유지합니다.':'Onnuri updates now use the official file, retaining the last verified data if a refresh fails.',
    '업데이트 후 이전 화면이 남는 캐시 문제를 보완했습니다.':'Improved cache handling after updates.',
    '출발지와 목적지를 정하고, 가는 길에 들를 주유소의 추가 이동시간·거리를 비교하는 기능을 추가했습니다. 도로 추정값이며 실시간 교통은 반영하지 않습니다.':'Added route detour time and distance comparison. Estimates use roads and exclude live traffic.',
    '선택한 주유소를 경유해 최종 목적지로 이동하는 네이버 내비·카카오맵 연결을 추가했습니다.':'Added Naver and KakaoMap routes via the selected station to the final destination.',
    '상생카드 가맹점에 할인 전 가격과 10% 적용 체감가를 함께 표시합니다. 예: 1,818원/L → 1,636.2원/L.':'Sangsaeng merchants show both the original and 10% effective price, e.g. KRW 1,818/L → KRW 1,636.2/L.',
    '온누리 지류·디지털 결제수단과 휘발유·경유 주유소/LPG 충전소를 구분해 찾을 수 있습니다.':'Filter by Onnuri paper/digital payment and petrol/diesel or LPG stations.',
    '상생카드 공식 목록의 자동 갱신, 가맹점별 확인일 표시, 좌표가 불확실한 장소의 경유 추천 제외를 반영했습니다.':'Added official Sangsaeng refreshes and merchant verification dates. Uncertain coordinates are excluded from route suggestions.',
    '모바일에서 경유 검색과 후보 목록을 보기 편하게 조정했습니다.':'Improved mobile route search and candidate lists.',
    '위치 권한을 허용하거나 출발지를 직접 검색하세요.':'Allow location access or search for a start manually.',
    '최근 전체 갱신 미완료':'Full refresh not recently completed',
    '새 파일 조회 실패, 이전 자료 유지':'File refresh failed; previous data retained',
    '한국어·영어 전환 버튼을 추가했습니다. 선택한 언어는 다음 방문에도 유지됩니다. 주유소명과 주소는 원문을 유지합니다.':'Added a Korean / English switch with a saved language preference. Station names and addresses remain in the original language.'
  };
  function translate(value) {
    const raw = String(value), text = raw.trim();
    let result = messages[text];
    if (/^지도 표시 \d+곳$/.test(text)) result = text.replace(/^지도 표시 (\d+)곳$/, '$1 mapped stations');
    if (/^(?:추가|주소(?:·업종)?) 확인 대기 \d+건$/.test(text)) result = text.replace(/^(?:추가|주소(?:·업종)?) 확인 대기 (\d+)건$/, '$1 locations awaiting review');
    if (/^공식 온누리 자료 /.test(text)) result = text.replace('공식 온누리 자료 ', 'Official Onnuri source: ');
    if (result === undefined) {
      if ((text.includes(' / ') || text.includes(' · ')) && !text.startsWith('추가 이동 약 ')) result = text.split(/( \/ | · )/).map(part => /[가-힣]/.test(part) ? translate(part) : part).join('');
      else if (/^\d+(곳|개)$/.test(text)) result = text.replace(/(곳|개)$/, Number.parseInt(text,10) === 1 ? ' station' : ' stations');
      else if (/^[\d,.]+원\/L$/.test(text)) result = 'KRW '+text.replace('원/L','/L');
      else if (/^선택됨: /.test(text)) result = text.replace('선택됨: ', 'Selected: ');
      else if (/^추가 이동 약 \d+분 · [\d.]+km$/.test(text)) result = text.replace('추가 이동 약 ','Approx. detour: ').replace('분',' min');
      else if (/^상생카드 조회[: ]/.test(text)) result = text.replace(/^상생카드 조회:? /,'Sangsaeng checked: ');
      else if (/^공식 자료 [\d-]+ 대조 \d+곳$/.test(text)) result = text.replace(/^공식 자료 ([\d-]+) 대조 (\d+)곳$/, 'Official source: $1, $2 matched');
      else if (/^매칭 미완료 \d+곳$/.test(text)) result = text.replace(/^매칭 미완료 (\d+)곳$/, '$1 unmatched');
      else if (/^총 \d+개$/.test(text)) result = text.replace(/^총 (\d+)개$/, '$1 stations');
      else if (/^총 \d+곳$/.test(text)) result = text.replace(/^총 (\d+)곳$/, '$1 total');
      else if (/^\d+곳 표시 중$/.test(text)) result = text.replace(/^(\d+)곳 표시 중$/, '$1 shown');
      else if (/^상생 \d+$/.test(text)) result = text.replace('상생 ', 'Sangsaeng ');
      else if (/^공식 검색 확인 /.test(text)) result = text.replace('공식 검색 확인 ','Official search checked: ');
      else if (/^공식 검색 [\d-]+ 확인 \d+곳$/.test(text)) result = text.replace(/^공식 검색 ([\d-]+) 확인 (\d+)곳$/, 'Official search: $1, $2 checked');
      else if (/^온누리 공식 검색 [\d-]+$/.test(text)) result = text.replace('온누리 공식 검색 ','Onnuri official search: ');
      else if (/^공식 자료 /.test(text)) result = text.replace('공식 자료 ','Official source: ');
      else if (/^과거 기록 /.test(text)) result = text.replace('과거 기록 ','Historical record: ').replace('미확인','unverified').replace('최근 unverified','not recently verified');
      else if (/^온누리 (공식 자료|공식 검색|과거 기록|디지털|지류|종류 미확인)/.test(text)) result = 'Onnuri '+translate(text.slice(4));
      else if (/^경로 주변 후보 \d+곳의 도로 이동시간 계산 중…$/.test(text)) result = text.replace(/^경로 주변 후보 (\d+)곳의 도로 이동시간 계산 중…$/, 'Calculating road times for $1 candidates…');
      else if (/^경로 주변 \d+곳 중 추가 이동이 적은 \d+곳입니다\. 교통·주유시간 제외\.$/.test(text)) result = text.replace(/^경로 주변 (\d+)곳 중 추가 이동이 적은 (\d+)곳입니다\. 교통·주유시간 제외\.$/, 'Top $2 detours from $1 candidates. Traffic and refueling excluded.');
      else if (/^".*" 복사됨$/.test(text)) result = text.replace(/ 복사됨$/, ' copied');
      else if (text.includes(' / ') || text.includes(' · ')) result = text.split(/( \/ | · )/).map(part => messages[part] ?? (part !== text && /[가-힣]/.test(part) ? translate(part) : part)).join('');
    }
    return result === undefined ? raw : raw.replace(text, result);
  }
  if (typeof module === 'object' && module.exports) {module.exports = {translate};return;}
  const button = document.getElementById('languageBtn');
  let language = 'ko';
  try {if (localStorage.getItem('gas-map-language') === 'en') language = 'en';} catch (_) {}
  const texts = new WeakMap(), attrs = new WeakMap();
  const attributes = ['placeholder','title','aria-label','alt'];
  const skipped = node => node.parentElement?.closest('script,style,svg,[data-no-i18n],.name,.address,.rank-name,.rank-addr,.nearby-name,.nearby-addr,.trip-result h3,.react-clist,.trip-choice');
  function scan(element) {
    if (!element || element.nodeType !== 1 || element.closest('script,style,svg,[data-no-i18n]')) return;
    // Option text must never change its underlying filter value.
    for (const option of element.querySelectorAll('option:not([value])')) option.setAttribute('value',option.value);
    const walker = document.createTreeWalker(element,NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (skipped(node) || !node.data.trim()) continue;
      let entry = texts.get(node);
      if (!entry || node.data !== entry.rendered) entry = {source:node.data};
      entry.rendered = language === 'en' ? translate(entry.source) : entry.source;
      if (node.data !== entry.rendered) node.data = entry.rendered;
      texts.set(node,entry);
    }
    for (const el of [element,...element.querySelectorAll('[placeholder],[title],[aria-label],[alt]')]) {
      if (el.closest('[data-no-i18n],script,style,svg')) continue;
      const saved = attrs.get(el) || {};
      for (const name of attributes) {
        if (!el.hasAttribute(name)) continue;
        const value = el.getAttribute(name);
        let entry = saved[name];
        if (!entry || entry.rendered !== value) entry = {source:value};
        entry.rendered = language === 'en' ? translate(entry.source) : entry.source;
        if (value !== entry.rendered) el.setAttribute(name,entry.rendered);
        saved[name] = entry;
      }
      attrs.set(el,saved);
    }
  }
  const config = {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:attributes};
  const observer = new MutationObserver(records => {
    observer.disconnect();
    const parents = new Set();
    for (const record of records) {
      if (record.type === 'characterData') parents.add(record.target.parentElement);
      else if (record.type === 'attributes') parents.add(record.target);
      else parents.add(record.target);
    }
    parents.forEach(scan);
    observer.observe(document.body,config);
  });
  function render() {
    observer.disconnect();
    scan(document.body);
    document.documentElement.lang = language;
    document.title = language === 'en' ? messages['전국 온누리 주유소 지도'] : '전국 온누리 주유소 지도';
    button.textContent = language === 'en' ? '한국어' : 'EN';
    button.setAttribute('aria-label',language === 'en' ? '한국어로 전환' : 'Switch to English');
    button.setAttribute('lang',language === 'en' ? 'ko' : 'en');
    observer.observe(document.body,config);
  }
  button.addEventListener('click',() => {
    language = language === 'ko' ? 'en' : 'ko';
    try {localStorage.setItem('gas-map-language',language);} catch (_) {}
    render();
  });
  render();
})(typeof globalThis !== 'undefined' ? globalThis : this);

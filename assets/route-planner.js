/* Trial road estimates: OSM/OSRM, no live traffic, no automatic background polling. */
(() => {
  'use strict';
  const core = GasRouteCore, byId = id => document.getElementById(id);
  let start = null, destination = null, generation = 0, lastRequest = 0, controller = null;
  const cache = new Map();
  const panel = byId('tripPanel'), status = byId('tripStatus'), results = byId('tripResults');
  function say(message) { status.textContent = message; }
  function clearResults() { generation++; controller?.abort(); results.replaceChildren(); panel.classList.remove("has-results"); byId("tripEdit").hidden=true; byId("tripRouteSummary").textContent=""; }
  function selectPoint(kind, point) {
    clearResults();
    if (kind === 'start') start = point; else destination = point;
    byId(kind === 'start' ? 'tripStart' : 'tripDestination').value = point.name;
    byId(kind === 'start' ? 'tripStartSelected' : 'tripDestinationSelected').textContent = '선택됨: ' + point.name;
    byId('tripChoices').replaceChildren();
    say(destination ? '주유소를 선택하거나 추가 이동시간을 비교하세요.' : '목적지를 검색해 선택하세요.');
  }
  const searchVersions = {start:0, destination:0};
  function search(kind) {
    const input = byId(kind === 'start' ? 'tripStart' : 'tripDestination');
    const query = input.value.trim();
    if (!query) { say('검색할 장소 또는 주소를 입력하세요.'); return; }
    const version = ++searchVersions[kind];
    say('장소 검색 중…');
    const service = new kakao.maps.services.Places();
    service.keywordSearch(query, (data, code) => {
      if (version !== searchVersions[kind] || input.value.trim() !== query) return;
      const choices = byId('tripChoices'); choices.replaceChildren();
      if (code !== kakao.maps.services.Status.OK) { say('장소를 찾지 못했습니다. 도로명주소나 다른 이름으로 검색하세요.'); return; }
      say('검색 결과에서 ' + (kind === 'start' ? '출발지' : '목적지') + '를 선택하세요.');
      const anchor = start || {lat:35.16,lng:126.85};
      data.sort((a,b)=>Math.floor(core.distance(anchor,{lat:Number(a.y),lng:Number(a.x)})/20)-Math.floor(core.distance(anchor,{lat:Number(b.y),lng:Number(b.x)})/20));
      data.slice(0,5).forEach(p => {
        const point = {lat:Number(p.y), lng:Number(p.x), name:p.place_name};
        if (!core.validPoint(point)) return;
        const button = document.createElement('button');button.type='button';button.className='trip-choice';
        button.textContent = p.place_name + ' · ' + (p.road_address_name || p.address_name);
        button.addEventListener('click',()=>selectPoint(kind,point));choices.append(button);
      });
    });
  }
  function methods(station) {
    const labels=[];
    if(station.payment_types.includes('saengsaeng')) labels.push('상생카드');
    if(station.payment_types.includes('onnuri')) {
      const m=station.onnuri_methods;
      labels.push('온누리 '+(m ? [m.paper&&'지류', (m.card||m.qr)&&'디지털'].filter(Boolean).join('·') : '종류 미확인')+' (최근 미확인)');
    }
    return labels.join(' / ');
  }
  function finishResults() {
    panel.classList.add('has-results');byId('tripEdit').hidden=false;
    byId('tripRouteSummary').textContent=start.name+' → '+destination.name;
  }
  function routeActions(station) {
    const actions=document.createElement('div');actions.className='trip-actions';
    const naver=document.createElement('a');naver.className='trip-link trip-primary';
    naver.textContent='네이버 내비로 경유';
    naver.href=core.naverUrl(start,station,destination,/Android/i.test(navigator.userAgent),location.hostname);
    naver.addEventListener('click',e=>{
      if(!isMobileDevice()){e.preventDefault();say('네이버 내비 연결은 휴대폰에서 사용하세요. PC에서는 카카오맵 경유 경로를 열 수 있습니다.');}
    });
    const kakao=document.createElement('a');kakao.className='trip-link trip-secondary';kakao.textContent='카카오맵 경유';
    kakao.href=core.kakaoUrl(start,station,destination);kakao.target='_blank';kakao.rel='noopener';
    actions.append(naver,kakao);return actions;
  }
  function showStation(station, estimate) {
    const card=document.createElement('article');card.className='trip-result';
    const title=document.createElement('h3');title.textContent=station.name;card.append(title);
    for(const value of [estimate ? `추가 이동 약 ${Math.ceil(estimate.addedSeconds/60)}분 · ${(estimate.addedMeters/1000).toFixed(1)}km` : '추가 이동시간 미계산',methods(station),station.address]){
      const p=document.createElement('p');p.textContent=value;card.append(p);
    }
    const prices=PRICES[station.name];
    if(prices){
      const block=document.createElement('div');block.className='trip-prices';
      for(const fuel of ['휘발유','경유','LPG']){
        if(!GasPriceDisplay.effectivePrice(prices[fuel],station))continue;
        const row=document.createElement('div');row.className='trip-fuel-price';
        row.innerHTML=fuel+' '+GasPriceDisplay.html(prices[fuel],station);block.append(row);
      }
      card.append(block);
    }
    const v=station.verification?.saengsaeng;
    const info=document.createElement('p');info.className='trip-note';
    info.textContent=v ? `상생카드 조회: ${v.checked_at.slice(0,10)}` : '온누리 마지막 확인: 2026-03-03 · 결제 가능 여부 재확인 필요';card.append(info);
    card.append(routeActions(station));return card;
  }
  async function requireStart() {
    if(start) return;
    if(byId('tripStart').value.trim()) throw new Error('출발지 검색 결과를 먼저 선택하세요.');
    const point=await locateUser({center:false});selectPoint('start',{...point,name:'내 위치'});
  }
  async function chooseStation(station) {
    panel.open=true;panel.scrollIntoView({block:'nearest'});
    if(!station.route_eligible || !core.validPoint(station)) {say('이 장소는 상세 좌표 또는 자동차 주유 업종 확인이 필요합니다.');return;}
    if(!destination){say('최종 목적지를 검색해 선택한 뒤 이 주유소를 다시 선택하세요.');byId('tripDestination').focus();return;}
    try { await requireStart();clearResults();results.append(showStation(station));finishResults();say('출발지 → '+station.name+' → '+destination.name); }
    catch(e){say(e.message || '출발지를 입력하거나 위치 권한을 허용하세요.');}
  }
  async function fetchRoad(url, signal) {
    if(cache.has(url)) return cache.get(url);
    await new Promise(resolve=>setTimeout(resolve,Math.max(0,1100-(Date.now()-lastRequest))));
    if(signal.aborted) throw new DOMException('취소됨','AbortError');
    lastRequest=Date.now();
    const response=await fetch(url,{signal});
    if(!response.ok) throw new Error('도로 경로 조회가 지연되고 있습니다. 잠시 후 다시 시도하거나 주유소를 직접 선택하세요.');
    const data=await response.json();
    if(data.code!=='Ok') throw new Error('자동차 경로를 찾지 못했습니다. 출발지·목적지를 확인하세요.');
    if(cache.size>20)cache.clear();cache.set(url,data);return data;
  }
  async function recommend(event) {
    event.preventDefault();
    if(!destination){search('destination');return;}
    const button=byId('tripRecommend');button.disabled=true;
    try {
      await requireStart();clearResults();
      const token=generation;controller=new AbortController();const active=controller;
      const deadline=setTimeout(()=>active.abort(),20000);
      try {
        if(core.distance(start,destination)<.1)throw new Error('출발지와 목적지가 너무 가깝습니다.');
        const candidates=core.shortlist(STATIONS,start,destination,byId('tripPayment').value,byId('tripMethod').value,byId('tripFuel').value);
        if(!candidates.length)throw new Error('이 결제수단으로 추천할 주유소가 없습니다. 다른 결제수단을 선택하세요.');
        say('경로 주변 후보 '+candidates.length+'곳의 도로 이동시간 계산 중…');
        const points=[start,destination,...candidates];
        const coordinates=points.map(p=>`${p.lng.toFixed(6)},${p.lat.toFixed(6)}`).join(';');
        const data=await fetchRoad(`https://router.project-osrm.org/table/v1/driving/${coordinates}?annotations=duration,distance`,active.signal);
        if(token!==generation)return;
        const ranked=core.rankMatrix(data,candidates);
        if(!ranked.length)throw new Error('진입 도로를 확인할 수 있는 후보가 없습니다. 주유소를 직접 선택하세요.');
        ranked.slice(0,5).forEach(row=>results.append(showStation(row.station,row)));finishResults();
        say(`경로 주변 ${candidates.length}곳 중 추가 이동이 적은 ${Math.min(5,ranked.length)}곳입니다. 교통·주유시간 제외.`);
      } finally {clearTimeout(deadline);}
    } catch(e) { if(e.name==='AbortError')say('조회가 취소되거나 시간이 초과됐습니다. 다시 비교하거나 주유소를 직접 선택하세요.');else say(e.message); }
    finally {button.disabled=false;}
  }
  ['start','destination'].forEach(kind=>{
    const input=byId(kind==='start'?'tripStart':'tripDestination');
    input.addEventListener('input',()=>{searchVersions[kind]++;if(kind==='start')start=null;else destination=null;clearResults();byId(kind==='start'?'tripStartSelected':'tripDestinationSelected').textContent='';byId('tripChoices').replaceChildren();});
    input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();search(kind);}});
  });
  byId('tripSearchStart').addEventListener('click',()=>search('start'));
  byId('tripSearchDestination').addEventListener('click',()=>search('destination'));
  byId('tripLocation').addEventListener('click',async()=>{try{const p=await locateUser({center:false});selectPoint('start',{...p,name:'내 위치'});}catch(e){say('위치 권한을 허용하거나 출발지를 직접 검색하세요.');}});
  byId('tripForm').addEventListener('submit',recommend);
  byId('tripEdit').addEventListener('click',()=>{clearResults();say('경로 또는 결제수단을 수정한 뒤 다시 비교하세요.');byId('tripDestination').focus();});
  ['tripPayment','tripMethod','tripFuel'].forEach(id=>byId(id).addEventListener('change',()=>{clearResults();say('조건이 변경됐습니다. 추가 이동시간을 다시 비교하세요.');}));
  const metadata=typeof MERCHANT_STATUS==='undefined'?{}:MERCHANT_STATUS;
  byId('merchantFreshness').textContent=`상생카드 조회 ${metadata.saengsaeng?.checked_at?.slice(0,10)||'미확인'} · 온누리 2026-03-03 이후 전체 갱신 미완료`;
  window.GasRoutePlanner={chooseStation};
})();

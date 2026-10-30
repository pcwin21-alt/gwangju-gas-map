/* Trial road estimates: OSM/OSRM, no live traffic, no automatic background polling. */
(() => {
  'use strict';
  const core = GasRouteCore, byId = id => document.getElementById(id);
  let start = null, destination = null, generation = 0, lastRequest = 0, controller = null, lastRoute=null, requestedStop=null;
  const cache = new Map();
  const panel = byId('tripPanel'), status = byId('tripStatus'), results = byId('tripResults');
  function syncControls() {
    const isOnnuri = byId('tripPayment').value === 'onnuri';
    byId('tripMethod').disabled = !isOnnuri;
    if (!isOnnuri) byId('tripMethod').value = 'any';
    byId('tripRecommend').textContent = destination ? (requestedStop?'이 주유소로 경유 연결':'경유 주유소 찾기') : '목적지 검색';
    const payment = {all:'모든 결제수단', onnuri:'온누리', saengsaeng:'상생카드'}[byId('tripPayment').value];
    const fuel = {all:'모든 유종', liquid:'휘발유·경유', lpg:'LPG'}[byId('tripFuel').value];
    const method = {any:'', paper:'지류', digital:'디지털'}[byId('tripMethod').value];
    byId('tripSettingsSummary').textContent = [start?.name || (byId('tripStart').value.trim() ? '출발지 선택 필요' : '내 위치'), payment, method, fuel].filter(Boolean).join(' · ');
  }
  let settingsInitialized = false;
  panel.addEventListener('toggle', () => {
    if (!panel.open || settingsInitialized) return;
    settingsInitialized = true;
    byId('tripPayment').value = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
    byId('tripMethod').value = {all:'any', paper:'paper', digital:'digital'}[byId('onnuriMethod').value] || 'any';
    if (byId('tripMethod').value !== 'any') byId('tripPayment').value = 'onnuri';
    byId('tripFuel').value = byId('fuelSelect').value === 'all' ? 'liquid' : byId('fuelSelect').value;
    syncControls();
  });
  function say(message) { status.textContent = message; }
  function clearResults() { generation++; controller?.abort();lastRoute=null;window.GasRouteMap?.clear(); results.replaceChildren(); panel.classList.remove("has-results"); for(const id of ['tripEdit','tripShowMap','tripClear','tripRefresh'])byId(id).hidden=true;for(const id of ['tripRecommend','tripRefresh'])byId(id).disabled=false; byId("tripRouteSummary").textContent=""; }
  function selectPoint(kind, point, auto=true) {
    clearResults();
    if (kind === 'start') start = point; else destination = point;
    byId(kind === 'start' ? 'tripStart' : 'tripDestination').value = point.name;
    byId(kind === 'start' ? 'tripStartSelected' : 'tripDestinationSelected').textContent = '선택됨: ' + point.name;
    byId('tripChoices').replaceChildren();
    syncControls();
    say(requestedStop?'경유할 주유소: '+requestedStop.name+' · 출발지와 목적지를 선택하세요.':destination ? '경유 주유소를 찾으면 추가 이동시간을 비교합니다.' : '목적지를 검색해 선택하세요.');
    if (kind === 'destination') byId('tripRecommend').focus();
    if(auto&&start&&destination)return recommend();
  }
  const searchVersions = {start:0, destination:0};
  let latestSearch=0;
  function search(kind) {
    const input = byId(kind === 'start' ? 'tripStart' : 'tripDestination');
    const query = input.value.trim();
    if (!query) { say('검색할 장소 또는 주소를 입력하세요.'); return; }
    const version = ++searchVersions[kind];
    const request=++latestSearch;
    say('장소 검색 중…');
    const service = new kakao.maps.services.Places();
    service.keywordSearch(query, (data, code) => {
      if (request!==latestSearch || version !== searchVersions[kind] || input.value.trim() !== query) return;
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
      labels.push('온누리 '+(m ? [m.paper&&'지류', GasMerchantDisplay.digital(m)&&'디지털'].filter(Boolean).join('·') : '종류 미확인'));
    }
    return labels.join(' / ');
  }
  function syncCriterion() {
    const distance=byId('tripCriterion').value==='distance';
    byId('tripCriterionSummary').textContent=(distance?`경로 ${byId('tripLimit').value}km 이내`:`추가 ${byId('tripLimit').value}분 미만`)+' · 조건 변경';
  }
  function finishResults(complete=false) {
    panel.classList.add('has-results');for(const id of ['tripEdit','tripShowMap','tripClear'])byId(id).hidden=false;
    byId('tripRefresh').hidden=true;
    syncCriterion();
    if(complete)byId('tripCriteria').open=false;
    byId('tripRouteSummary').textContent=start.name+' → '+destination.name+(lastRoute?` · 약 ${Math.ceil(lastRoute.seconds/60)}분 · ${(lastRoute.meters/1000).toFixed(1)}km`:'');
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
  function showStation(station, estimate, index) {
    const card=document.createElement('article');card.className='trip-result';
    const title=document.createElement('h3');title.textContent=(index?`${index}. `:'')+station.name;card.append(title);
    const seconds=estimate?Math.floor(estimate.addedSeconds):0;
    const added=seconds<60?`${seconds}초`:`${Math.floor(seconds/60)}분 ${seconds%60}초`;
    for(const value of [estimate ? `추가 이동 약 ${added} · ${(estimate.addedMeters/1000).toFixed(1)}km${Number.isFinite(estimate.routeKm)?` · 경로에서 ${estimate.routeKm.toFixed(1)}km`:''}` : '추가 이동시간 미계산',methods(station),station.address]){
      const p=document.createElement('p');p.textContent=value;card.append(p);
    }
    const prices=PRICES[station.id];
    if(prices){
      const block=document.createElement('div');block.className='trip-prices';
      for(const fuel of ['휘발유','경유','LPG']){
        if(!GasPriceDisplay.effectivePrice(prices[fuel],station))continue;
        const row=document.createElement('div');row.className='trip-fuel-price';
        row.innerHTML=fuel+' '+GasPriceDisplay.html(prices[fuel],station);block.append(row);
      }
      card.append(block);
    }
    const info=document.createElement('p');info.className='trip-note';
    info.textContent=GasMerchantDisplay.verificationText(station);card.append(info);
    const actions=routeActions(station);
    if(index){const focus=document.createElement('button');focus.type='button';focus.textContent='지도에서 보기';focus.addEventListener('click',()=>{window.GasTripWindow?.minimize();window.GasRouteMap?.focus(station.id);});actions.append(focus);}
    card.append(actions);return card;
  }
  async function requireStart() {
    if(start) return;
    if(byId('tripStart').value.trim()) throw new Error('출발지 검색 결과를 먼저 선택하세요.');
    const version = generation;
    let point;
    try{point=await locateUser({center:false,alertOnFail:false});}
    catch(e){throw new Error('현재 위치를 확인하지 못했습니다. 출발지를 직접 검색하거나 위치 권한을 확인하세요.');}
    if (version !== generation) throw new DOMException('취소됨','AbortError');
    selectPoint('start',{...point,name:'내 위치'},false);
  }
  async function chooseStation(station) {
    if(window.GasTripWindow)window.GasTripWindow.open();else panel.open=true;
    if(!station.route_eligible || !core.validPoint(station)) {say('이 장소는 상세 좌표 또는 자동차 주유 업종 확인이 필요합니다.');return;}
    requestedStop=station;clearResults();syncControls();
    if(!destination){say(station.name+' 경유를 선택했습니다. 최종 목적지를 검색하세요.');byId('tripDestination').focus();return;}
    if(!start){byId('tripSettings').open=true;say(station.name+' 경유를 선택했습니다. 출발지를 선택하거나 경유 연결을 누르세요.');return;}
    try { await requireStart();clearResults();results.append(showStation(station));finishResults();say('출발지 → '+station.name+' → '+destination.name); }
    catch(e){if (!start) byId('tripSettings').open=true;say(e.message || '출발지를 입력하거나 위치 권한을 허용하세요.');}
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
    event?.preventDefault();
    if(byId('tripRecommend').disabled)return;
    if(!destination){search('destination');return;}
    const button=byId('tripRecommend');button.disabled=true;byId('tripRefresh').disabled=true;
    if(requestedStop){
      try{await requireStart();await chooseStation(requestedStop);}
      catch(e){if(!start)byId('tripSettings').open=true;say(e.message||'출발지를 직접 검색하세요.');}
      finally{button.disabled=false;byId('tripRefresh').disabled=false;}
      return;
    }
    let requestToken=null;
    try {
      await requireStart();clearResults();
      button.disabled=true;byId('tripRefresh').disabled=true;
      const token=generation;requestToken=token;controller=new AbortController();const active=controller;
      const deadline=setTimeout(()=>active.abort(),45000);
      try {
        if(core.distance(start,destination)<.1)throw new Error('출발지와 목적지가 너무 가깝습니다.');
        const coordinates=[start,destination].map(p=>`${p.lng.toFixed(6)},${p.lat.toFixed(6)}`).join(';');
        say('예상 자동차 경로를 불러오는 중…');
        const routeData=await fetchRoad(`https://router.project-osrm.org/route/v1/driving/${coordinates}?overview=full&geometries=geojson&steps=false`,active.signal);
        if(token!==generation)return;
        lastRoute=core.roadRoute(routeData);window.GasRouteMap?.show(lastRoute,start,destination);finishResults();
        const mode=byId('tripCriterion').value,limit=Number(byId('tripLimit').value);
        const candidates=core.shortlist(STATIONS,start,destination,byId('tripPayment').value,byId('tripMethod').value,byId('tripFuel').value,{coordinates:lastRoute.coordinates,radiusKm:mode==='distance'?limit:10});
        if(!candidates.length){finishResults(true);say('이 경로 주변에 조건에 맞는 주유소가 없습니다. 거리·결제수단을 변경하세요.');return;}
        const ranked=[];
        for(let offset=0;offset<candidates.length;offset+=24) {
          say(`경로 주변 ${candidates.length}곳의 추가 이동시간 비교 중… (${offset}/${candidates.length})`);
          const batch=candidates.slice(offset,offset+24),points=[start,destination,...batch];
          const coords=points.map(p=>`${p.lng.toFixed(6)},${p.lat.toFixed(6)}`).join(';');
          const matrix=await fetchRoad(`https://router.project-osrm.org/table/v1/driving/${coords}?annotations=duration,distance`,active.signal);
          if(token!==generation)return;
          ranked.push(...core.rankMatrix(matrix,batch).map(row=>({...row,routeKm:core.distanceToRoute(row.station,lastRoute.coordinates)})));
        }
        const matched=ranked.filter(row=>core.matchesRecommendation(row,mode,limit)).sort((a,b)=>mode==='distance'?a.routeKm-b.routeKm||a.addedSeconds-b.addedSeconds:a.addedSeconds-b.addedSeconds||a.addedMeters-b.addedMeters);
        matched.forEach((row,i)=>results.append(showStation(row.station,row,i+1)));
        window.GasRouteMap?.show(lastRoute,start,destination,matched.map(row=>row.station));finishResults(true);
        say(matched.length?`추천 ${matched.length}곳 · ${candidates.length}곳 비교 · ${mode==='distance'?`경로에서 ${limit}km 이내`:`추가 ${limit}분 미만 (경로 10km 이내 조사)`}${matched.length>5?' · 지도 상위 5곳, 전체는 목록에서 확인':''} · 교통·주유시간 제외.`:'조건에 맞는 주유소가 없습니다. 거리나 추가 이동시간을 늘려 다시 적용하세요.');
      } finally {clearTimeout(deadline);}
    } catch(e) { if(requestToken!==null&&requestToken!==generation)return;if(lastRoute)byId('tripRefresh').hidden=false;if (!start) byId('tripSettings').open=true;if(e.name==='AbortError')say('조회가 취소되거나 시간이 초과됐습니다. 다시 비교하거나 주유소를 직접 선택하세요.');else say(e.message); }
    finally {if(requestToken===null||requestToken===generation){button.disabled=false;byId('tripRefresh').disabled=false;}}
  }
  ['start','destination'].forEach(kind=>{
    const input=byId(kind==='start'?'tripStart':'tripDestination');
    input.addEventListener('input',()=>{latestSearch++;searchVersions[kind]++;if(kind==='start')start=null;else destination=null;clearResults();byId(kind==='start'?'tripStartSelected':'tripDestinationSelected').textContent='';byId('tripChoices').replaceChildren();syncControls();say('');});
    input.setAttribute('enterkeyhint','search');
    input.addEventListener('keydown',e=>{if(e.key==='Enter' && !e.isComposing && e.keyCode!==229){e.preventDefault();input.blur();if(kind==='destination')byId('tripForm').requestSubmit();else search(kind);}});
  });
  byId('tripSearchStart').addEventListener('click',()=>search('start'));
  byId('tripLocation').addEventListener('click',async()=>{
    const button=byId('tripLocation');if(button.disabled)return;
    const version=generation;button.disabled=true;
    try{const p=await locateUser({center:false,alertOnFail:false});if(version===generation)selectPoint('start',{...p,name:'내 위치'});}
    catch(e){if(version===generation)say('위치 권한을 허용하거나 출발지를 직접 검색하세요.');}
    finally{button.disabled=false;}
  });
  byId('tripForm').addEventListener('submit',recommend);
  byId('tripShowMap').addEventListener('click',()=>{window.GasRouteMap?.fit();panel.open=false;});
  byId('tripClear').addEventListener('click',()=>{requestedStop=null;clearResults();syncControls();say('경로를 지웠습니다. 목적지를 선택해 다시 찾을 수 있습니다.');});
  byId('tripRefresh').addEventListener('click',recommend);
  byId('resetBtn').addEventListener('click',()=>{latestSearch++;clearResults();start=null;destination=null;requestedStop=null;for(const id of ['tripStart','tripDestination'])byId(id).value='';for(const id of ['tripStartSelected','tripDestinationSelected'])byId(id).textContent='';byId('tripChoices').replaceChildren();syncControls();say('');});
  byId('tripCriterion').addEventListener('change',()=>{
    const distance=byId('tripCriterion').value==='distance',select=byId('tripLimit');
    select.replaceChildren();for(const value of distance?[1,2,5,10]:[5,10,15]){const option=document.createElement('option');option.value=String(value);option.textContent=distance?`${value}km 이내`:`${value}분 미만`;select.append(option);}
    select.value=distance?'2':'5';byId('tripLimitLabel').textContent=distance?'경로 반경':'추가 이동 한도';
    syncCriterion();clearResults();if(start&&destination)recommend();
  });
  byId('tripLimit').addEventListener('change',()=>{syncCriterion();clearResults();if(start&&destination)recommend();});
  byId('tripEdit').addEventListener('click',()=>{clearResults();say('경로 또는 결제수단을 수정한 뒤 다시 비교하세요.');byId('tripDestination').focus();});
  ['tripPayment','tripMethod','tripFuel'].forEach(id=>byId(id).addEventListener('change',()=>{clearResults();syncControls();say('조건이 변경됐습니다. 추가 이동시간을 다시 비교하세요.');}));
  syncControls();
  syncCriterion();
  const metadata=typeof MERCHANT_STATUS==='undefined'?{}:MERCHANT_STATUS;
  const onnuri=metadata.onnuri;
  const onnuriSummary=onnuri?.status==='confirmed' ? `공식 검색 ${onnuri.checked_at.slice(0,10)} 확인 ${onnuri.matched_count}곳 · 과거 기록 ${onnuri.unmatched_count}곳` : (onnuri?.source_date ? `공식 자료 ${onnuri.source_date} 대조 ${onnuri.matched_count}곳` : '최근 전체 갱신 미완료');
  byId('merchantFreshness').textContent=`상생카드 조회 ${metadata.saengsaeng?.checked_at?.slice(0,10)||'미확인'} · 온누리 ${onnuriSummary}${onnuri?.refresh_error ? ' · 새 조회 실패, 이전 자료 유지' : ''}`;
  window.GasRoutePlanner={chooseStation,clearForMapSearch(){clearResults();say('지도 검색 조건이 변경되어 경로 표시를 지웠습니다. 경유 찾기를 다시 누르면 비교할 수 있습니다.');}};
})();

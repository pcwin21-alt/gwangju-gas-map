(() => {
  'use strict';
  const byId=id=>document.getElementById(id),core=GasStationResults,state=GasNationalState;
  const regionInput=byId('regionSelect'),method=byId('onnuriMethod'),fuel=byId('fuelSelect');
  const panel=byId('nationalResults'),body=byId('resultsBody'),list=byId('stationList');
  const scope=byId('resultsScope'),order=byId('resultsOrder'),areaButton=byId('searchAreaBtn');
  const hasMap=Boolean(window.kakao?.maps);
  let limit=20,restoring=true,areaBounds=null,selectedId=null,returnFromList=false,returnScroll=0,orderChosen=false,fallbackPayment='all';
  const locationPoint=()=>hasMap&&typeof currentLocation!=='undefined'?currentLocation:null;
  const payment=()=>hasMap?currentFilter:fallbackPayment;
  const query=()=>byId('searchInput').value.trim().toLowerCase();
  const routeActive=()=>Boolean(window.GasRouteMap?.isActive());
  const bankSummary=()=>MERCHANT_STATUS.supplemental_onnuri?.confirmed_count?
    ` · KB국민카드 조회 추가 ${MERCHANT_STATUS.supplemental_onnuri.confirmed_count}곳 (${MERCHANT_STATUS.supplemental_onnuri.checked_at.slice(0,10)})`:'';
  GasNational.regions.forEach(name=>regionInput.add(new Option(name,name)));
  function boundsNow() {
    if(!hasMap)return null;
    const bounds=map.getBounds(),sw=bounds.getSouthWest(),ne=bounds.getNorthEast();
    return {south:sw.getLat(),west:sw.getLng(),north:ne.getLat(),east:ne.getLng()};
  }
  function items() {
    return hasMap?allMarkers.filter(m=>m.visible):STATIONS.filter(s=>GasNational.matches(s,state)&&
      (payment()==='all'||s.payment_types.includes(payment()))&&GasNational.searchMatches(s,query())).map(station=>({station}));
  }
  function text(tag,value,className) {const el=document.createElement(tag);el.textContent=value;if(className)el.className=className;return el;}
  function emptyActions(parent) {
    const actions=document.createElement('div');actions.className='empty-actions';
    const add=(label,action)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('click',action);actions.append(b);};
    if(scope.value==='map')add('선택 지역 전체 보기',()=>{scope.value='region';render(true);});
    if(query())add('검색어 지우기',()=>{byId('searchInput').value='';byId('searchInput').dispatchEvent(new Event('input',{bubbles:true}));});
    if(payment()!=='all'||state.method!=='all'||state.fuel!=='all'||(hasMap&&currentDistrict!=='all'))add('필터 초기화',()=>byId('filtersReset').click());
    add('지역 바꾸기',()=>byId('regionOpen').click());parent.append(actions);
  }
  function stationRow(row) {
    const station=row.item.station,node=document.createElement(hasMap?'button':'a');
    if(hasMap)node.type='button';else{node.href='https://map.kakao.com/link/search/'+encodeURIComponent(station.name+' '+station.address);node.target='_blank';node.rel='noopener';}
    node.className='station-list-row';node.dataset.stationId=station.id;
    const name=text('strong',station.name);name.dataset.noI18n='';
    const address=text('span',station.address||'상세주소 미확인','station-address');address.dataset.noI18n='';
    node.append(name);
    if(row.km!==null)node.append(text('span',core.distanceText(row.km),'station-distance'));
    node.append(address,text('span',GasMerchantDisplay.paymentSummary(station)+(station.fuel_kind==='lpg'?' · LPG 충전소':''),'station-payment'));
    if(station.verification?.onnuri?.status!=='confirmed')node.append(text('span',GasMerchantDisplay.checkCaption(station),'station-proof'));
    const prices=typeof PRICES==='undefined'?null:PRICES[station.id];
    const priceLabel=core.priceText(station,prices,typeof PRICE_INFO==='undefined'?null:PRICE_INFO[station.id]?.source_dates);
    if(priceLabel)node.append(text('span',priceLabel,'station-price'));
    if(hasMap)node.setAttribute('aria-pressed',String(selectedId===station.id));
    if(hasMap)node.addEventListener('click',()=>{
      selectedId=station.id;returnScroll=body.scrollTop;
      for(const el of list.children)el.setAttribute('aria-pressed',String(el===node));
      map.setCenter(new kakao.maps.LatLng(station.lat,station.lng));map.setLevel(4);
      showStationOverlay(row.item.overlay,{fromResults:true});
    });
    return node;
  }
  function refreshMapCount() {
    if(!hasMap)return;
    const all=items(),count=core.select(all,{bounds:boundsNow()}).length;
    byId('listScope').textContent='현재 지도 안 '+count+'곳';
  }
  function render(reset=false) {
    const scroll=reset?0:body.scrollTop,focused=document.activeElement?.dataset?.stationId,all=items(),point=locationPoint();
    order.querySelector('option[value="distance"]').disabled=!point;
    if(!point&&order.value==='distance')order.value='name';
    const rows=core.select(all,{bounds:scope.value==='map'?areaBounds:null,location:point,order:order.value});
    byId('resultDataStatus').textContent=`온누리 공식 검색 ${MERCHANT_STATUS.onnuri?.source_date||'미확인'}${MERCHANT_STATUS.onnuri?.refresh_error?' · 최근 조회 실패, 이전 자료 유지':''}`+bankSummary();
    byId('nationalSummary').textContent=rows.length>limit?`${limit}곳 표시 중`:'';
    byId('listCount').textContent=`${scope.value==='map'?'찾은 범위':'전체'} ${rows.length}곳`;
    list.replaceChildren(...rows.slice(0,limit).map(stationRow));
    if(!rows.length){list.append(text('p','조건에 맞는 주유소가 없습니다.'));emptyActions(list);}
    byId('moreStations').hidden=rows.length<=limit;
    if(hasMap)refreshMapCount();else{byId('listScope').textContent=(state.region==='all'?'전국':state.region)+' 조건 결과 · 지도 대신 주소 목록';byId('countBadge').textContent=rows.length+'곳';}
    body.scrollTop=scroll;
    if(focused)[...list.children].find(el=>el.dataset.stationId===focused)?.focus({preventScroll:true});
  }
  function setSize(full) {
    panel.dataset.size=full?'full':'half';byId('resultsSize').textContent=full?'작게':'크게';
    byId('resultsSize').setAttribute('aria-label',full?'목록 절반으로 줄이기':'목록 전체로 펼치기');byId('resultsSize').setAttribute('aria-expanded',String(full));
    resizeResults();
  }
  function resizeResults() {
    const area=document.querySelector('.map-area'),available=Math.max(100,area.clientHeight-88);
    const half=Math.min(available,Math.max(180,area.clientHeight*.55));
    const heading=panel.querySelector('summary').getBoundingClientRect().height||56;
    panel.style.setProperty('--results-available',available+'px');
    panel.style.setProperty('--results-body-height',Math.max(44,(panel.dataset.size==='full'?available:half)-heading)+'px');
  }
  const resultObserver=new ResizeObserver(resizeResults);resultObserver.observe(document.querySelector('.map-area'));resultObserver.observe(panel.querySelector('summary'));
  panel.addEventListener('toggle',resizeResults);resizeResults();
  byId('resultsSize').addEventListener('click',()=>setSize(panel.dataset.size!=='full'));
  panel.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel.open){event.preventDefault();event.stopPropagation();panel.open=false;panel.querySelector('summary').focus({preventScroll:true});}});
  scope.addEventListener('change',()=>{if(scope.value==='map')areaBounds=boundsNow();limit=20;render(true);});
  order.addEventListener('change',()=>{orderChosen=true;limit=20;render(true);});
  byId('moreStations').addEventListener('click',()=>{limit+=20;render();});
  window.GasResultsPanel={
    onDetailsOpen(fromResults){returnFromList=fromResults;},
    restoreSelection(){
      if(!returnFromList||routeActive())return false;
      returnFromList=false;panel.open=true;body.scrollTop=returnScroll;
      ([...list.children].find(el=>el.dataset.stationId===selectedId)||panel.querySelector('summary')).focus({preventScroll:true});return true;
    }
  };
  window.addEventListener('gas:locationchange',()=>{if(!orderChosen)order.value='distance';render();});
  window.addEventListener('gas:routechange',()=>{areaButton.hidden=true;});
  areaButton.addEventListener('click',()=>{if(routeActive())window.GasRoutePlanner?.clearForMapSearch();areaBounds=boundsNow();scope.value='map';limit=20;render(true);panel.open=true;areaButton.hidden=true;});
  function syncURL() {
    const u=new URL(location.href);
    for(const k of ['region','method','fuel']){if(state[k]==='all'&&k!=='region')u.searchParams.delete(k);else u.searchParams.set(k,state[k]);}
    if(payment()==='all')u.searchParams.delete('payment');else u.searchParams.set('payment',payment());
    if(!hasMap||currentDistrict==='all')u.searchParams.delete('district');else u.searchParams.set('district',currentDistrict);
    // Keep GPS, input text and trip endpoints out of shared URLs.
    if(u.href!==location.href)history[restoring?'replaceState':'pushState'](null,'',u);
  }
  function districts() {
    const select=byId('districtSelect');select.replaceChildren(new Option('전체 시·군·구','all'));select.disabled=state.region==='all';
    if(!select.disabled)[...new Set(STATIONS.filter(s=>s.region===state.region).map(s=>s.address?.split(/\s+/)[1]).filter(Boolean))].sort().forEach(name=>select.add(new Option(name,name)));
    currentDistrict='all';setDistrictHighlight('all');
  }
  function change() {
    const regionChanged=state.region!==regionInput.value;state.region=regionInput.value;state.method=method.value;state.fuel=fuel.value;limit=20;
    // A deliberate filter change starts a new search; map panning alone never does.
    scope.value='region';areaBounds=null;returnFromList=false;
    if(hasMap){if(regionChanged||restoring)districts();applyFilters();clearRankMapOverlays();mapViewport.fit();}else render(true);
    syncURL();
  }
  [regionInput,method,fuel].forEach(el=>el.addEventListener('change',change));
  if(hasMap){
    const original=applyFilters;applyFilters=function(){scope.value='region';areaBounds=null;limit=20;original();render(true);};
    for(const name of ['dragend','zoom_changed'])kakao.maps.event.addListener(map,name,()=>{if(!routeActive())areaButton.hidden=false;});
    kakao.maps.event.addListener(map,'idle',refreshMapCount);
    document.querySelectorAll('.filter-btn').forEach(el=>el.addEventListener('click',syncURL));byId('districtSelect').addEventListener('change',syncURL);
  }else{
    scope.querySelector('option[value="map"]').disabled=true;panel.open=true;
    byId('map').textContent='지도를 불러오지 못했습니다. 목록에서 주소와 길찾기를 확인하세요.';
    for(const id of ['myLocBtn','rankBtn','fitResultsBtn','districtSelect'])byId(id).disabled=true;byId('tripPanel').hidden=true;
    byId('searchInput').addEventListener('input',()=>{limit=20;render(true);});
    document.querySelectorAll('.filter-btn').forEach(b=>b.addEventListener('click',()=>{fallbackPayment=b.dataset.filter;document.querySelectorAll('.filter-btn').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});render(true);syncURL();}));
  }
  byId('resetBtn').addEventListener('click',()=>{regionInput.value='광주';method.value=fuel.value='all';change();});
  function restore() {
    restoring=true;const url=new URL(location.href),district=url.searchParams.get('district');
    regionInput.value=GasNational.regionFromURL(url.searchParams.get('region'));method.value=['paper','digital'].includes(url.searchParams.get('method'))?url.searchParams.get('method'):'all';fuel.value=['liquid','lpg'].includes(url.searchParams.get('fuel'))?url.searchParams.get('fuel'):'all';
    const selected=['onnuri','saengsaeng'].includes(url.searchParams.get('payment'))?url.searchParams.get('payment'):'all';
    if(hasMap)currentFilter=selected;else fallbackPayment=selected;
    document.querySelectorAll('.filter-btn').forEach(b=>{b.classList.toggle('active',b.dataset.filter===selected);b.setAttribute('aria-pressed',String(b.dataset.filter===selected));});change();
    if(hasMap&&district&&[...byId('districtSelect').options].some(o=>o.value===district))triggerDistrictSelect(district);syncURL();restoring=false;
  }
  window.addEventListener('popstate',restore);restore();
})();

(() => {
  'use strict';
  const bankSummary=()=>MERCHANT_STATUS.supplemental_onnuri?.confirmed_count?
    ` · KB국민카드 조회 추가 ${MERCHANT_STATUS.supplemental_onnuri.confirmed_count}곳 (${MERCHANT_STATUS.supplemental_onnuri.checked_at.slice(0,10)})`:'';
  function emptyActions(parent,query,filtered) {
    const actions=document.createElement('div');actions.className='empty-actions';
    const add=(label,action)=>{const button=document.createElement('button');button.type='button';button.textContent=label;button.addEventListener('click',action);actions.append(button);};
    if(query)add('검색어 지우기',()=>{const input=document.getElementById('searchInput');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));});
    if(filtered)add('필터 초기화',()=>document.getElementById('filtersReset').click());
    add('지역 바꾸기',()=>document.getElementById('regionOpen').click());parent.append(actions);
  }
  if (!window.kakao?.maps) {
    // Public merchant lookup remains usable when a map domain is unavailable.
    const state=GasNationalState, regionInput=document.getElementById('regionSelect');
    GasNational.regions.forEach(name=>regionInput.add(new Option(name,name)));
    let payment='all';
    const url=new URL(location.href);
    regionInput.value=GasNational.regionFromURL(url.searchParams.get('region'));
    if(['onnuri','saengsaeng'].includes(url.searchParams.get('payment')))payment=url.searchParams.get('payment');
    if(['paper','digital'].includes(url.searchParams.get('method')))document.getElementById('onnuriMethod').value=url.searchParams.get('method');
    if(['liquid','lpg'].includes(url.searchParams.get('fuel')))document.getElementById('fuelSelect').value=url.searchParams.get('fuel');
    document.querySelectorAll('.filter-btn').forEach(b=>{
      b.classList.toggle('active',b.dataset.filter===payment);b.setAttribute('aria-pressed',String(b.dataset.filter===payment));
    });
    const panel=document.getElementById('nationalResults');panel.open=true;
    document.getElementById('map').textContent='지도를 불러오지 못했습니다. 조건에 맞는 주유소에서 주소와 길찾기를 확인하세요.';
    for(const id of ['myLocBtn','rankBtn','fitResultsBtn','districtSelect'])document.getElementById(id).disabled=true;
    document.getElementById('tripPanel').hidden=true;
    function renderFallback() {
      state.region=regionInput.value;state.method=document.getElementById('onnuriMethod').value;state.fuel=document.getElementById('fuelSelect').value;
      const q=document.getElementById('searchInput').value.trim().toLowerCase();
      const rows=STATIONS.filter(s=>GasNational.matches(s,state)&&(payment==='all'||s.payment_types.includes(payment))&&GasNational.searchMatches(s,q));
      const list=document.getElementById('stationList');list.replaceChildren();
      rows.forEach(s=>{
        const a=document.createElement('a');a.className='station-list-row';a.target='_blank';a.rel='noopener';
        a.href='https://map.kakao.com/link/search/'+encodeURIComponent(s.name+' '+s.address);
        a.textContent=s.name+' · '+s.address+' · 길찾기';list.append(a);
        if(s.verification?.onnuri?.provider==='kbcard')a.textContent+=' · '+GasMerchantDisplay.onnuriNote(s);
      });
      if(!rows.length){const p=document.createElement('p');p.textContent='조건에 맞는 주유소가 없습니다. 검색어나 필터를 바꿔보세요.';list.append(p);emptyActions(list,q,payment!=='all'||state.method!=='all'||state.fuel!=='all');}
      document.getElementById('countBadge').textContent=rows.length+'곳';
      document.getElementById('listCount').textContent='총 '+rows.length+'곳';
      document.getElementById('nationalSummary').textContent=rows.length+'곳 표시 중 · 온누리 공식 검색 '+MERCHANT_STATUS.onnuri.source_date+' · 지도 대신 목록 제공'+(MERCHANT_STATUS.onnuri.refresh_error?' · 최근 조회 실패, 이전 자료 유지':'')+bankSummary();
      document.getElementById('moreStations').hidden=true;
      document.getElementById('pendingSummary').parentElement.hidden=true;
    }
    for(const id of ['regionSelect','onnuriMethod','fuelSelect'])document.getElementById(id).addEventListener('change',renderFallback);
    document.getElementById('searchInput').addEventListener('input',renderFallback);
    document.querySelectorAll('.filter-btn').forEach(b=>b.addEventListener('click',()=>{
      payment=b.dataset.filter;document.querySelectorAll('.filter-btn').forEach(x=>x.classList.toggle('active',x===b));renderFallback();
    }));
    renderFallback();return;
  }
  const state=GasNationalState;
  const regionInput=document.getElementById('regionSelect');
  const method=document.getElementById('onnuriMethod');
  const fuel=document.getElementById('fuelSelect');
  const summary=document.getElementById('nationalSummary');
  const list=document.getElementById('stationList');
  const pending=document.getElementById('pendingList');
  let limit=20, restoring=true;
  GasNational.regions.forEach(name=>regionInput.add(new Option(name,name)));
  function districts() {
    const select=document.getElementById('districtSelect');
    select.replaceChildren(new Option('전체 시·군·구','all'));
    select.disabled=state.region==='all';
    if (!select.disabled) {
      [...new Set(STATIONS.filter(s=>s.region===state.region).map(s=>s.address?.split(/\s+/)[1]).filter(Boolean))]
        .sort().forEach(name=>select.add(new Option(name,name)));
    }
    currentDistrict='all';
    setDistrictHighlight('all');
  }
  function syncURL() {
    const u=new URL(location.href);
    for(const k of ['region','method','fuel']) {
      if(state[k]==='all'&&k!=='region')u.searchParams.delete(k);else u.searchParams.set(k,state[k]);
    }
    if(currentFilter==='all')u.searchParams.delete('payment');else u.searchParams.set('payment',currentFilter);
    if(currentDistrict==='all')u.searchParams.delete('district');else u.searchParams.set('district',currentDistrict);
    // Exact GPS, search text and trip endpoints are never included.
    if (u.href!==location.href) history[restoring?'replaceState':'pushState'](null,'',u);
  }
  function render() {
    const visible=allMarkers.filter(m=>m.visible);
    const waiting=(typeof NATIONAL_PENDING==='undefined'?[]:NATIONAL_PENDING).filter(r=>
      state.region==='all'||r.region===state.region||(['광주','전남'].includes(state.region)&&r.region==='전남광주'));
    summary.textContent=`${Math.min(limit,visible.length)}곳 표시 중 · 온누리 공식 검색 ${MERCHANT_STATUS.onnuri?.source_date||'미확인'}${MERCHANT_STATUS.onnuri?.refresh_error?' · 최근 조회 실패, 이전 자료 유지':''}`+bankSummary();
    const title=document.getElementById('pendingSummary');
    title.textContent=`추가 확인 대기 ${waiting.length}건`;
    pending.replaceChildren();
    waiting.forEach(r=>{
      const li=document.createElement('li');
      li.textContent=`${r.name} · ${r.market} · ${r.region} — ${r.reason}`;
      pending.append(li);
    });
    list.replaceChildren();
    visible.slice(0,limit).forEach(item=>{
      const button=document.createElement('button');button.type='button';button.className='station-list-row';
      const name=document.createElement('strong');name.textContent=item.station.name;
      const address=document.createElement('span');address.textContent=item.station.address;
      const types=document.createElement('span');
      types.textContent=item.station.payment_types.includes('onnuri')?
        '온누리 '+[item.station.onnuri_methods?.paper===true&&'지류',item.station.onnuri_methods?.digital===true&&'디지털'].filter(Boolean).join('·'):'광주상생카드';
      if(item.station.verification?.onnuri?.provider==='kbcard') types.textContent+=' · KB국민카드 조회 기준';
      button.append(name,address,types);
      button.addEventListener('click',()=>{
        if(activeOverlay)activeOverlay.setMap(null);
        map.setCenter(new kakao.maps.LatLng(item.station.lat,item.station.lng));map.setLevel(4);
        showStationOverlay(item.overlay);
      });list.append(button);
    });
    if(!visible.length){const p=document.createElement('p');p.textContent='조건에 맞는 확인된 등록이 없습니다. 지역이나 결제 유형을 바꿔보세요.';list.append(p);emptyActions(list,currentSearch,currentFilter!=='all'||currentDistrict!=='all'||state.method!=='all'||state.fuel!=='all');}
    const more=document.getElementById('moreStations');more.hidden=visible.length<=limit;
    document.getElementById('listCount').textContent=`총 ${visible.length}곳`;
  }
  const original=applyFilters;
  applyFilters=function(){original();render();};
  function change() {
    const regionChanged=state.region!==regionInput.value;
    state.region=regionInput.value;state.method=method.value;state.fuel=fuel.value;limit=20;
    if(regionChanged||restoring)districts();
    applyFilters();clearRankMapOverlays();mapViewport.fit();syncURL();
  }
  [regionInput,method,fuel].forEach(el=>el.addEventListener('change',change));
  document.getElementById('moreStations').addEventListener('click',()=>{limit+=20;render();});
  document.querySelectorAll('.filter-btn').forEach(el=>el.addEventListener('click',syncURL));
  document.getElementById('districtSelect').addEventListener('change',syncURL);
  document.getElementById('resetBtn').addEventListener('click',()=>{
    regionInput.value='광주';method.value=fuel.value='all';change();
  });
  function restore() {
    restoring=true;
    const url=new URL(location.href);
    const district=url.searchParams.get('district');
    regionInput.value=GasNational.regionFromURL(url.searchParams.get('region'));
    method.value=['paper','digital'].includes(url.searchParams.get('method'))?url.searchParams.get('method'):'all';
    fuel.value=['liquid','lpg'].includes(url.searchParams.get('fuel'))?url.searchParams.get('fuel'):'all';
    const payment=url.searchParams.get('payment');
    currentFilter=['onnuri','saengsaeng'].includes(payment)?payment:'all';
    document.querySelectorAll('.filter-btn').forEach(b=>{
      b.classList.toggle('active',b.dataset.filter===currentFilter);
      b.setAttribute('aria-pressed',String(b.dataset.filter===currentFilter));
    });
    change();
    if(district && [...document.getElementById('districtSelect').options].some(o=>o.value===district))triggerDistrictSelect(district);
    syncURL();restoring=false;
  }
  window.addEventListener('popstate',restore);
  restore();
})();

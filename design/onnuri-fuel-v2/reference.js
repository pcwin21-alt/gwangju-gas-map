/* Review only: use preserved prices and dates; never infer a discount or fetch stations. */
(() => {
  // Keep the list action aligned to the map, independent of the result panel width.
  document.querySelector('.map-area').append(document.getElementById('searchAreaBtn'));
  const helpLabels=['지역화폐 · 지역색','온누리 · 주황','전체 보기의 중복 · 두 색'];
  document.querySelectorAll('.help-dot').forEach((dot,index)=>{
    dot.style.background=index===0?FUEL_PIN_THEMES.currencies['gwangju-saengsaeng'].fill:index===1?FUEL_PIN_THEMES.onnuri.fill:'linear-gradient(90deg,#EB6620 50%,#285BB5 50%)';
    dot.style.border='1px solid #596673';
    if(dot.parentElement.lastChild.nodeType===Node.TEXT_NODE)dot.parentElement.lastChild.textContent=helpLabels[index];
  });
  const list=document.getElementById('stationList');
  function decorateRows(){
    for(const row of list.querySelectorAll('[data-station-id]')){
      if(row.querySelector('.v2-result-price'))continue;
      const station=STATIONS.find(s=>s.id===row.dataset.stationId);if(!station)continue;
      const fuel=station.fuel_kind==='lpg'?'LPG':'휘발유',price=PRICES[station.id]?.[fuel];
      const block=document.createElement('span');block.className='v2-result-price';
      const value=document.createElement('b'),meta=document.createElement('small'),date=document.createElement('small');
      const known=Number.isFinite(price)&&price>0;
      value.textContent=known?price.toLocaleString('ko-KR'):'유가 미확인';
      meta.textContent=known?fuel+' · 원/L':'';
      const dates=PRICE_INFO[station.id]?.source_dates;
      date.textContent=known?(dates?.length?dates.map(d=>d.slice(0,4)+'.'+d.slice(4,6)+'.'+d.slice(6)).join(' / '):'기준일 미확인'):'';
      if(!known)block.classList.add('unknown');block.append(value,meta,date);row.append(block);
    }
  }
  new MutationObserver(decorateRows).observe(list,{childList:true});decorateRows();
  if(!window.kakao?.maps)return;
  const pins=[],markerCache=new Map();let routePinsHidden=false;
  const payment=()=>document.querySelector('.filter-btn.active[data-filter="local"]')
    ? document.getElementById('regionalPayment').value : document.querySelector('.filter-btn.active')?.dataset.filter||'all';
  function applyTheme(button,theme){
    button.style.setProperty('--pin-edge',theme.priceEdge||theme.edge);
    button.style.setProperty('--pin-surface',theme.surface);
    button.style.setProperty('--pin-ink',theme.priceInk||(theme.symbol==='diamond'?theme.edge:theme.ink));
    button.dataset.paymentTheme=theme.key;
    button.title=theme.label+' · 보관된 기준일 유가';
  }
  function colorMarkers(){
    const selected=payment();
    for(const item of allMarkers){
      const theme=fuelPinTheme(item.station,selected);
      if(!markerCache.has(theme.key))markerCache.set(theme.key,new kakao.maps.MarkerImage('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(fuelPinSvg(theme)),new kakao.maps.Size(28,36),{offset:new kakao.maps.Point(14,36)}));
      item.marker.setImage(markerCache.get(theme.key));
    }
  }
  for(const item of allMarkers){
    const s=item.station,fuel=s.fuel_kind==='lpg'?'LPG':'휘발유',p=PRICES[s.id]?.[fuel];
    if(!Number.isFinite(p)||p<=0)continue;
    const button=document.createElement('button');button.type='button';button.className='fuel-price-pin';
    const grade=document.createElement('small'),amount=document.createElement('strong');grade.textContent=fuel+' · 원/L';amount.textContent=p.toLocaleString('ko-KR');button.append(grade,amount);
    applyTheme(button,fuelPinTheme(s,payment()));
    button.setAttribute('aria-label',s.name+' '+fuel+' '+p+'원/L, 보관된 기준일 가격');
    button.addEventListener('click',()=>showStationOverlay(item.overlay));
    const overlay=new kakao.maps.CustomOverlay({position:new kakao.maps.LatLng(s.lat,s.lng),content:button,yAnchor:1,zIndex:60});
    pins.push({item,overlay,button});
  }
  function syncPins(){
    colorMarkers();
    if(document.querySelector('.map-area').classList.contains('fuel-route-active')){
      routePinsHidden=true;
      for(const item of allMarkers)item.marker.setMap(null);
      for(const pin of pins)pin.overlay.setMap(null);
      return;
    }
    if(routePinsHidden){for(const item of allMarkers)item.marker.setMap(item.visible?map:null);routePinsHidden=false;}
    const bounds=map.getBounds(),near=map.getLevel()<=7&&new URL(location.href).searchParams.get('prices')!=='off';
    const placed=[],frame=document.getElementById('map').getBoundingClientRect();
    for(const {item,overlay,button} of pins){
      const theme=fuelPinTheme(item.station,payment());applyTheme(button,theme);
      button.setAttribute('aria-label',item.station.name+' '+theme.label+' '+button.textContent+', 보관된 기준일 가격');
      let show=near&&item.visible&&bounds.contain(new kakao.maps.LatLng(item.station.lat,item.station.lng));
      if(show){
        overlay.setMap(map);
        const r=button.getBoundingClientRect();
        show=r.left>=frame.left+8&&r.right<=frame.right-8&&r.top>=frame.top+8&&r.bottom<=frame.bottom-8&&!placed.some(p=>r.left<p.right+8&&r.right>p.left-8&&r.top<p.bottom+8&&r.bottom>p.top-8);
        if(show)placed.push(r);
      }
      overlay.setMap(show?map:null);
      item.marker.setMap(item.visible&&!show?map:null);
    }
  }
  kakao.maps.event.addListener(map,'idle',syncPins);
  addEventListener('fuelroutevisibility',syncPins);
  new MutationObserver(syncPins).observe(document.getElementById('mapFilters'),{subtree:true,attributes:true,attributeFilter:['class']});
  const start=()=>{
    const params=new URL(location.href).searchParams;
    if(params.get('focus')==='prices'){
      const sample=allMarkers.find(i=>i.station.name==='서양새마을금고 주유소');
      if(sample){map.setCenter(new kakao.maps.LatLng(sample.station.lat,sample.station.lng));map.setLevel(6);}
    }
    if(params.get('view')==='list')document.getElementById('searchAreaBtn').click();
    syncPins();
  };
  if(document.readyState==='complete')start();else addEventListener('load',start,{once:true});
})();

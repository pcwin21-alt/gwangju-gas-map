/* Review only: use preserved prices and dates; never infer a discount or fetch stations. */
(() => {
  // Keep the list action aligned to the map, independent of the result panel width.
  document.querySelector('.map-area').append(document.getElementById('searchAreaBtn'));
  const helpLabels = ['지역화폐', '온누리', '둘 다 가능'];
  document.querySelectorAll('.help-dot').forEach((dot, index) => {
    dot.classList.add('fuel-pin-face');
    dot.dataset.symbol = ['diamond', 'circle', 'double'][index];
    dot.style.removeProperty('background');
    dot.parentElement.lastChild.textContent = helpLabels[index];
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
  const frame = document.getElementById('map');
  const layers = new Map();
  const pricesEnabled = new URL(location.href).searchParams.get('prices') !== 'off';
  const payment = () => currentFilter;

  function groupPins(gap, width, height) {
    const projection = map.getProjection();
    const groups = [];
    for (const item of allMarkers) {
      if (!item.visible) continue;
      const position = item.marker.getPosition();
      const {x, y} = projection.containerPointFromCoords(position);
      if (x < 0 || y < 0 || x > width || y > height) continue;
      const group = groups.find(pin => Math.abs(x - pin.x) < gap && Math.abs(y - pin.y) < gap);
      if (group) group.items.push(item);
      else groups.push({x, y, position, items:[item]});
    }
    return groups;
  }

  function showGroup(group) {
    closeStationOverlay();
    const level = map.getLevel();
    if (level >= 10) {
      map.setCenter(group.position);
      map.setLevel(Math.max(9, level - 2));
    } else {
      window.GasResultsPanel.showCluster(group.items.map(item => item.station.id));
    }
  }

  function makePin(group, kind) {
    const item = group.items[0];
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'fuel-map-pin fuel-' + kind + '-pin';
    const face = document.createElement('span');
    face.className = 'fuel-pin-face';
    face.setAttribute('aria-hidden', 'true');
    button.append(face);
    const overlay = new kakao.maps.CustomOverlay({
      position:group.position, content:button, clickable:true, yAnchor:0.5, zIndex:60,
    });
    const layer = {button, face, overlay, group};
    button.addEventListener('click', event => {
      event.stopPropagation();
      if (reportMode) return;
      if (kind === 'cluster') showGroup(layer.group);
      else showStationOverlay(item.overlay);
    });
    if (kind !== 'cluster') button.dataset.stationPin = item.station.id;
    if (kind === 'price') {
      const fuel = item.station.fuel_kind === 'lpg' ? 'LPG' : '휘발유';
      const amount = PRICES[item.station.id][fuel];
      const grade = document.createElement('small');
      grade.textContent = fuel + ' · 원/L';
      const value = document.createElement('strong');
      value.textContent = amount.toLocaleString('ko-KR');
      face.append(grade, value);
      button.dataset.priceLabel = fuel + ' ' + amount.toLocaleString('ko-KR') + '원/L, 보관된 기준일 가격';
    }
    return layer;
  }

  function updatePin(layer, group, kind, selected) {
    layer.group = group;
    const {button, face, overlay} = layer;
    const isSelected = Boolean(activeOverlay && group.items.some(item => item.overlay === activeOverlay));
    button.classList.toggle('is-selected', isSelected);
    const zIndex = isSelected ? 65 : 60;
    if (overlay.getZIndex() !== zIndex) overlay.setZIndex(zIndex);
    if (kind === 'cluster') {
      const count = group.items.length + '곳';
      face.textContent = group.items.length.toLocaleString('ko-KR');
      button.setAttribute('aria-label', count + (map.getLevel() >= 10 ? ' 있는 구역 확대' : ' 목록 보기'));
      return;
    }
    const station = group.items[0].station;
    const theme = fuelPinTheme(station, selected);
    if (button.dataset.paymentTheme !== theme.key) {
      button.dataset.paymentTheme = theme.key;
      button.dataset.symbol = theme.symbol;
      button.style.setProperty('--pin-accent', theme.fill);
      button.style.setProperty('--pin-secondary', theme.second || theme.fill);
      button.style.setProperty('--pin-edge', theme.edge);
      button.setAttribute('aria-label', [station.name, theme.label, button.dataset.priceLabel].filter(Boolean).join(' · '));
    }
    button.setAttribute('aria-pressed', String(isSelected));
  }

  function syncPins() {
    const showingRoute = window.GasRouteMap?.isActive() ||
      document.querySelector('.map-area').classList.contains('fuel-route-active');
    const level = map.getLevel();
    const width = frame.clientWidth;
    const height = frame.clientHeight;
    const compact = level >= 8;
    const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
    const targetSize = Math.max(44, 2.75 * rem);
    const gap = Math.max(level >= 11 ? 54 : 48, targetSize + 4);
    const groups = showingRoute ? [] : groupPins(gap, width, height);
    // Reserve every touch target before considering a wider price label.
    const halfWidth = Math.max(76, 5.5 * rem) / 2;
    const halfHeight = Math.max(44, 2.75 * rem) / 2;
    const priceGroups = [];
    if (!compact && pricesEnabled) {
      const candidates = groups.filter(({items}) => {
        const station = items[0].station;
        const price = PRICES[station.id]?.[station.fuel_kind === 'lpg' ? 'LPG' : '휘발유'];
        return items.length === 1 && Number.isFinite(price) && price > 0;
      });
      candidates.sort((a, b) => Number(b.items[0].overlay === activeOverlay) - Number(a.items[0].overlay === activeOverlay));
      for (const group of candidates) {
        const {x, y} = group;
        if (x < halfWidth + 8 || width - x < halfWidth + 8 ||
            y < halfHeight + 8 || height - y < halfHeight + 8) continue;
        const conflicts = groups.some(other => other !== group &&
          Math.abs(x - other.x) < halfWidth + targetSize / 2 + 4 && Math.abs(y - other.y) < halfHeight + targetSize / 2 + 4);
        const priceConflict = priceGroups.some(other =>
          Math.abs(x - other.x) < 2 * halfWidth + 8 && Math.abs(y - other.y) < 2 * halfHeight + 8);
        if (!conflicts && !priceConflict) priceGroups.push(group);
      }
    }

    const plan = new Map();
    for (const group of groups) {
      const kind = group.items.length > 1 ? 'cluster' : priceGroups.includes(group) ? 'price' : 'station';
      const key = kind + ':' + group.items[0].station.id;
      plan.set(key, {group, kind});
    }
    for (const [key, layer] of layers) {
      if (plan.has(key)) continue;
      layer.overlay.setMap(null);
      layers.delete(key);
    }
    const selected = payment();
    for (const [key, {group, kind}] of plan) {
      let layer = layers.get(key);
      if (!layer) {
        layer = makePin(group, kind);
        layers.set(key, layer);
      }
      updatePin(layer, group, kind, selected);
      layer.button.classList.toggle('is-compact', compact);
      if (!layer.overlay.getMap()) layer.overlay.setMap(map);
    }
  }
  // Any fallback markers attached before this script finished loading belong to the old layer.
  for (const {marker} of allMarkers) {
    if (marker.getMap()) marker.setMap(null);
  }
  window.GasStationPins = { refresh: syncPins };
  kakao.maps.event.addListener(map, 'idle', syncPins);
  addEventListener('fuelroutevisibility', syncPins);
  new MutationObserver(syncPins).observe(document.getElementById('stationDetails'), {childList:true});
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

/* Optional, lazily loaded vector view. Kakao continues to serve local search and the original view. */
(() => {
  'use strict';
  const byId=id=>document.getElementById(id), area=document.querySelector('.map-area');
  const button=byId('rotationBtn'), container=byId('rotationMap'), details=byId('rotationDetails');
  let vector=null, enabled=false, loading=null, locationMarker=null, noteTimer=0, syncing=false;
  const nativeCenter=window.kakao?.maps?map.setCenter.bind(map):null;
  const nativeLevel=window.kakao?.maps?map.setLevel.bind(map):null;
  const reduced=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const duration=()=>reduced()?0:250;
  function note(message,temporary=false) {
    clearTimeout(noteTimer);byId('mapModeStatus').textContent=message;byId('mapModeStatus').hidden=!message;
    if(temporary)noteTimer=setTimeout(()=>note(''),5000);
  }
  function data() {
    return {type:'FeatureCollection',features:allMarkers.filter(row=>row.visible).map(row=>({type:'Feature',geometry:{type:'Point',coordinates:[row.station.lng,row.station.lat]},properties:{id:row.station.id,name:row.station.name,color:COLOR[row.markerType]||'#f59e0b'}}))};
  }
  function sync() {if(vector?.getSource('stations'))vector.getSource('stations').setData(data());details.hidden=true;}
  function compass() {
    const angle=Math.round(vector.getBearing());
    byId('compassNeedle').style.transform=`rotate(${-angle}deg)`;
    button.setAttribute('aria-label',`북쪽으로 정렬 (${angle}°)`);
    button.title='북쪽으로 정렬';
  }
  function show(station) {
    if(activeOverlay){activeOverlay.setMap(null);activeOverlay=null;}
    byId('nationalResults').open=false;
    const close=document.createElement('button');close.type='button';close.className='rotation-detail-close';close.textContent='닫기';close.setAttribute('aria-label','주유소 상세 닫기');
    close.addEventListener('click',()=>{details.hidden=true;});
    details.replaceChildren(close,buildInfoHtml(station));details.hidden=false;
  }
  function script() {
    if(window.maplibregl)return Promise.resolve();
    return new Promise((resolve,reject)=>{
      const css=document.createElement('link');css.rel='stylesheet';css.href='assets/maplibre-gl-5.12.0.css';document.head.append(css);
      const js=document.createElement('script');js.src='assets/maplibre-gl-5.12.0.js';js.onload=resolve;js.onerror=()=>{js.remove();reject(new Error('회전 지도를 불러오지 못했습니다. 다시 눌러 주세요.'));};document.head.append(js);
    });
  }
  async function prepare() {
    await script();
    container.hidden=false;
    const center=map.getCenter();
    try {
      vector=new maplibregl.Map({container,style:'https://tiles.openfreemap.org/styles/liberty',center:[center.getLng(),center.getLat()],zoom:18-map.getLevel(),maxPitch:0,touchPitch:false,renderWorldCopies:false,maxBounds:[[120,30],[138,46]],attributionControl:true});
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('회전 지도 연결이 지연됩니다. 기존 지도를 사용하거나 다시 시도하세요.')),15000);
        const fail=()=>{clearTimeout(timer);reject(new Error('이 브라우저에서 회전 지도를 불러올 수 없습니다. 기존 지도를 계속 사용할 수 있습니다.'));};
        vector.once('error',fail);vector.once('load',()=>{clearTimeout(timer);vector.off('error',fail);resolve();});
      });
      vector.addSource('stations',{type:'geojson',data:data()});
      vector.addLayer({id:'stations',type:'circle',source:'stations',paint:{'circle-radius':8,'circle-color':['get','color'],'circle-stroke-color':'#ffffff','circle-stroke-width':2}});
      vector.addLayer({id:'station-names',type:'symbol',source:'stations',minzoom:12,layout:{'text-field':['get','name'],'text-font':['Noto Sans Regular'],'text-size':13,'text-anchor':'top','text-offset':[0,1]},paint:{'text-color':'#18243c','text-halo-color':'#ffffff','text-halo-width':2}});
      vector.on('click','stations',event=>{
        const id=event.features?.[0]?.properties.id;
        const found=allMarkers.find(row=>row.station.id===id);if(found)show(found.station);
      });
      vector.on('click',event=>{if(!vector.queryRenderedFeatures(event.point,{layers:['stations']}).length)details.hidden=true;});
      vector.on('rotate',compass);
      vector.on('moveend',()=>{
        if(!enabled||syncing)return;
        syncing=true;
        try {const center=vector.getCenter();nativeCenter(new kakao.maps.LatLng(center.lat,center.lng));nativeLevel(Math.max(1,Math.min(14,Math.round(18-vector.getZoom()))));}
        finally{syncing=false;}
      });
      vector.on('dragstart',()=>{byId('myLocBtn').classList.remove('located');details.hidden=true;});
      vector.on('webglcontextlost',()=>{disable();note('회전 지도 연결이 끊겨 기존 지도로 돌아왔습니다.');});
      new ResizeObserver(()=>{if(vector&&enabled)vector.resize();}).observe(area);
    } catch(error) {vector?.remove();vector=null;container.hidden=true;throw error;}
  }
  function activate() {
    const center=map.getCenter();vector.jumpTo({center:[center.getLng(),center.getLat()],zoom:18-map.getLevel(),bearing:0});
    enabled=true;container.hidden=false;area.classList.add('vector-active');
    byId('plainMapBtn').hidden=false;byId('compassNeedle').textContent='N ↑';
    vector.resize();sync();compass();
    if(typeof currentLocation!=='undefined'&&currentLocation)markLocation(currentLocation);
    note('두 손가락으로 확대·회전 · N을 누르면 북쪽',true);
  }
  function disable() {
    if(!enabled)return;
    const center=vector.getCenter(),level=Math.round(18-vector.getZoom());
    enabled=false;area.classList.remove('vector-active');container.hidden=true;details.hidden=true;byId('plainMapBtn').hidden=true;
    byId('compassNeedle').textContent='회전';byId('compassNeedle').style.transform='';button.setAttribute('aria-label','회전 지도 켜기');button.title='회전 지도 켜기';note('');
    map.relayout();map.setCenter(new kakao.maps.LatLng(center.lat,center.lng));map.setLevel(Math.min(14,Math.max(1,level)));
  }
  button.addEventListener('click',async()=>{
    if(enabled){vector.easeTo({bearing:0,pitch:0,duration:duration()});return;}
    button.disabled=true;note('회전 지도 불러오는 중…');
    try {if(!vector){loading ||= prepare().finally(()=>{loading=null;});await loading;}activate();}
    catch(error){console.warn('Rotation view unavailable',error);note('회전 지도를 불러오지 못했습니다. 다시 눌러 주세요.');}
    finally{button.disabled=false;}
  });
  byId('plainMapBtn').addEventListener('click',disable);
  for(const id of ['rankBtn','reportMapPinBtn'])byId(id).addEventListener('click',disable,{capture:true});
  function markLocation(point) {
    if(!vector)return;
    if(!locationMarker)locationMarker=new maplibregl.Marker({color:'#1672d7'}).setLngLat([point.lng,point.lat]).addTo(vector);
    else locationMarker.setLngLat([point.lng,point.lat]);
  }
  // Bridge existing result, filter, location and route actions to whichever view is visible.
  if(window.kakao?.maps) {
    for(const method of ['setCenter','setLevel','setBounds']) {
      const original=map[method].bind(map);
      map[method]=(...args)=>{
        const result=original(...args);if(!enabled||syncing)return result;
        if(method==='setCenter')vector.jumpTo({center:[args[0].getLng(),args[0].getLat()]});
        if(method==='setLevel')vector.jumpTo({zoom:18-args[0]});
        if(method==='setBounds') {
          const sw=args[0].getSouthWest(),ne=args[0].getNorthEast();
          vector.fitBounds([[sw.getLng(),sw.getLat()],[ne.getLng(),ne.getLat()]],{padding:64,maxZoom:16,bearing:vector.getBearing(),duration:duration()});
        }
        return result;
      };
    }
    const originalFilters=applyFilters;applyFilters=()=>{originalFilters();if(enabled)sync();};
    const originalOverlay=showStationOverlay;showStationOverlay=overlay=>{
      if(!enabled)return originalOverlay(overlay);
      const row=allMarkers.find(item=>item.overlay===overlay);if(row)show(row.station);
    };
    const originalLocation=setCurrentLocation;setCurrentLocation=(...args)=>{const point=originalLocation(...args);if(enabled)markLocation(point);return point;};
  } else {button.disabled=true;byId('mapZoomIn').disabled=true;byId('mapZoomOut').disabled=true;}
  for(const [id,delta] of [['mapZoomIn',1],['mapZoomOut',-1]])byId(id).addEventListener('click',()=>{
    if(enabled)vector.easeTo({zoom:Math.max(3,Math.min(18,vector.getZoom()+delta)),duration:duration()});
    else if(window.kakao?.maps)map.setLevel(Math.max(1,Math.min(14,map.getLevel()-delta)));
  });
  container.addEventListener('pointerdown',()=>{if(document.activeElement?.matches('input,textarea'))document.activeElement.blur();},{capture:true,passive:true});
  function expand(force) {
    const app=document.querySelector('.app'),expanded=typeof force==='boolean'?force:!app.classList.contains('map-expanded');
    app.classList.toggle('map-expanded',expanded);byId('expandMapBtn').setAttribute('aria-pressed',String(expanded));
    byId('expandMapBtn').setAttribute('aria-label',expanded?'지도 작게 보기':'지도 크게 보기');byId('expandMapBtn').title=expanded?'지도 작게 보기':'지도 크게 보기';
  }
  byId('expandMapBtn').addEventListener('click',()=>expand());
  document.addEventListener('keydown',event=>{if(event.key==='Escape')expand(false);});
})();

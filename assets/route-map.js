/* Route overlays on the Kakao map. Kept in memory only. */
(() => {
  'use strict';
  let state=null, overlays=[],fitFrame=0,focusedPin=null;
  const visibleLimit=5;
  function refresh() {if(typeof allMarkers!=='undefined')for(const row of allMarkers)row.marker.setMap(!state&&row.visible?map:null);}
  const notify=()=>{refresh();window.dispatchEvent(new CustomEvent('gas:routechange'));};
  function clear() {cancelAnimationFrame(fitFrame);for(const overlay of overlays)overlay.setMap(null);overlays=[];focusedPin=null;state=null;notify();}
  function fit() {
    if(!state||!window.kakao?.maps)return;
    cancelAnimationFrame(fitFrame);
    fitFrame=requestAnimationFrame(()=>{fitFrame=requestAnimationFrame(()=>{
      if(!state)return;
      const bounds=new kakao.maps.LatLngBounds();
      for(const c of state.route.coordinates)bounds.extend(new kakao.maps.LatLng(c[1],c[0]));
      for(const p of [state.start,state.end])bounds.extend(new kakao.maps.LatLng(p.lat,p.lng));
      map.relayout();map.setBounds(bounds,64,48,64,48);
    });});
  }
  function collection() {
    if(!state)return {type:'FeatureCollection',features:[]};
    return {type:'FeatureCollection',features:[
      {type:'Feature',geometry:{type:'LineString',coordinates:state.route.coordinates},properties:{kind:'route'}},
      ...[state.start,state.end,...state.stations].map((p,i)=>({type:'Feature',geometry:{type:'Point',coordinates:[p.lng,p.lat]},properties:{kind:i<2?'endpoint':'candidate',label:i===0?'출발':i===1?'도착':String(i-1),id:p.id||'',name:p.name}}))
    ]};
  }
  function show(route,start,end,stations=[]) {
    clear();state={route,start,end,stations};
    if(window.kakao?.maps) {
      const path=route.coordinates.map(c=>new kakao.maps.LatLng(c[1],c[0]));
      overlays.push(new kakao.maps.Polyline({map,path,strokeWeight:10,strokeColor:'#ffffff',strokeOpacity:.95,zIndex:4}),
        new kakao.maps.Polyline({map,path,strokeWeight:6,strokeColor:'#2864dc',strokeOpacity:1,zIndex:5}));
      [start,end,...stations.slice(0,visibleLimit)].forEach((p,i)=>overlays.push(makePin(p,i)));
    }
    notify();fit();
  }
  function makePin(p,i) {
    const node=document.createElement(i<2?'span':'button');node.className='trip-map-pin';node.textContent=i===0?'출발':i===1?'도착':String(i-1);
    if(i>1){node.type='button';node.setAttribute('aria-label',`${i-1}. ${p.name} 상세`);node.addEventListener('click',()=>focus(p.id));}
    return new kakao.maps.CustomOverlay({map,position:new kakao.maps.LatLng(p.lat,p.lng),content:node,zIndex:8,yAnchor:1});
  }
  function focus(id) {
    if(!state)return;
    const station=state.stations.find(p=>p.id===id);if(!station)return;
    if(focusedPin)focusedPin.setMap(null);
    if(state.stations.indexOf(station)>=visibleLimit){focusedPin=makePin(station,state.stations.indexOf(station)+2);overlays.push(focusedPin);}
    map.setCenter(new kakao.maps.LatLng(station.lat,station.lng));map.setLevel(4);
    const row=allMarkers.find(r=>r.station.id===id);if(row)showStationOverlay(row.overlay);
  }
  window.GasRouteMap={show,clear,fit,collection,focus,refresh,visibleLimit,cancelFit:()=>cancelAnimationFrame(fitFrame),isActive:()=>Boolean(state)};
})();

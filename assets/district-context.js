/* Identify existing Gwangju boundaries locally; never reverse-geocode or request GPS. */
(() => {
  'use strict';
  if(!window.kakao?.maps||!window.GasDistrictGeoJSON)return;
  const core=GasDistrictContextCore,area=document.querySelector('.map-area'),box=document.getElementById('districtContext');
  const names=document.getElementById('districtContextName'),near=document.getElementById('districtContextNear');
  const shapes=window.GasDistrictGeoJSON.features.map(f=>{
    const content=document.createElement('span');content.className='district-map-label';content.textContent=f.properties.gu;content.style.setProperty('--district-color',DISTRICT_COLORS[f.properties.gu]);
    return {name:f.properties.gu,polygons:f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates,overlay:new kakao.maps.CustomOverlay({content,position:map.getCenter(),xAnchor:.5,yAnchor:.5,zIndex:1,clickable:false})};
  });
  function hide(){box.hidden=true;shapes.forEach(s=>s.overlay.setMap(null));}
  let frame=0;
  function update() {
    const width=area.clientWidth,height=area.clientHeight;
    if(map.getLevel()>8||width<180||height<180){hide();return;}
    const projection=map.getProjection();
    const features=shapes.map(s=>({name:s.name,polygons:s.polygons.map(rings=>rings.map(ring=>ring.map(c=>{const p=projection.containerPointFromCoords(new kakao.maps.LatLng(c[1],c[0]));return [p.x,p.y];})))}));
    const result=core.context(features,width,height);
    shapes.forEach(s=>{const label=result.labels.find(l=>l.name===s.name);if(!label){s.overlay.setMap(null);return;}s.overlay.setPosition(projection.coordsFromContainerPoint(new kakao.maps.Point(...label.point)));s.overlay.setMap(map);});
    if(!result.home&&!result.neighbors.length){box.hidden=true;return;}
    const title=result.home?'지도 중심 · '+result.home:'광주 자치구 경계 부근';
    const detail=result.home?(result.neighbors.length?result.neighbors.join('·')+' 경계 부근':'광주 자치구 경계 부근'):result.neighbors.join('·');
    if(names.textContent!==title)names.textContent=title;
    if(near.textContent!==detail)near.textContent=detail;
    box.hidden=false;
  }
  function schedule(){cancelAnimationFrame(frame);frame=requestAnimationFrame(update);}
  kakao.maps.event.addListener(map,'idle',schedule);
  kakao.maps.event.addListener(map,'dragstart',hide);
  kakao.maps.event.addListener(map,'zoom_start',hide);
  new ResizeObserver(schedule).observe(area);schedule();
})();

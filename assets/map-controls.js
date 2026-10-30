/* Controls for the single Kakao map. */
(() => {
  'use strict';
  const byId=id=>document.getElementById(id),area=document.querySelector('.map-area');
  window.addEventListener('gas:routechange',()=>area.classList.toggle('trip-route-active',Boolean(window.GasRouteMap?.isActive())));
  if(window.kakao?.maps) {
    const originalFilters=applyFilters;
    applyFilters=()=>{originalFilters();window.GasRouteMap?.refresh();};
  } else {
    byId('mapZoomIn').disabled=true;byId('mapZoomOut').disabled=true;
  }
  for(const [id,delta] of [['mapZoomIn',-1],['mapZoomOut',1]])byId(id).addEventListener('click',()=>{
    if(window.kakao?.maps)map.setLevel(Math.max(1,Math.min(14,map.getLevel()+delta)));
  });
  function expand(force) {
    const app=document.querySelector('.app'),expanded=typeof force==='boolean'?force:!app.classList.contains('map-expanded');
    app.classList.toggle('map-expanded',expanded);byId('expandMapBtn').setAttribute('aria-pressed',String(expanded));
    byId('expandMapBtn').setAttribute('aria-label',expanded?'지도 작게 보기':'지도 크게 보기');byId('expandMapBtn').title=expanded?'지도 작게 보기':'지도 크게 보기';
  }
  byId('expandMapBtn').addEventListener('click',()=>expand());
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!event.defaultPrevented&&!document.querySelector('dialog[open]'))expand(false);});
})();

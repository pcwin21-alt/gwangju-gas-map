/* User intent -> existing map/list/route actions. No location request on load. */
(() => {
  'use strict';
  const byId=id=>document.getElementById(id),near=byId('nearbyModeBtn'),route=byId('routeModeBtn');
  const trip=byId('tripPanel'),list=byId('nationalResults'),status=byId('searchFlowStatus');
  const hasMap=Boolean(window.kakao?.maps);
  let version=0,pending=false;
  const routing=()=>Boolean(window.GasRouteMap?.isActive());
  function mode(value){near.setAttribute('aria-pressed',String(value==='nearby'));route.setAttribute('aria-pressed',String(value==='route'));}
  function say(text=''){status.textContent=text;status.hidden=!text;}
  function prepare(){
    byId('mapFilters').hidden=true;byId('filtersToggle').setAttribute('aria-expanded','false');
    if(hasMap&&typeof closeStationOverlay==='function')closeStationOverlay();
    const input=document.activeElement;
    if(input?.matches?.('input,textarea,[contenteditable="true"]'))input.blur();
  }
  function openRoute(){
    if(!hasMap||trip.hidden)return;
    version++;prepare();say();list.open=false;mode('route');window.GasTripWindow?.open();
  }
  async function nearby(){
    if(pending)return;
    const request=++version;prepare();window.GasTripWindow?.minimize();
    if(!hasMap){list.open=true;list.querySelector('summary').focus({preventScroll:true});return;}
    if(routing())window.GasRoutePlanner?.clearForMapSearch();
    pending=true;near.disabled=true;near.setAttribute('aria-busy','true');mode('nearby');say('현재 위치를 확인하고 있습니다.');
    try{
      const point=await locateUser({center:false,alertOnFail:false,shouldApply:()=>request===version});
      if(request!==version)return;
      map.setCenter(new window.kakao.maps.LatLng(point.lat,point.lng));map.setLevel(4);
      mode('nearby');
      window.GasResultsPanel?.showNearby();say();
    }catch(_){
      if(request!==version)return;
      mode('map');say('위치 확인 실패. 주소로 검색하세요.');
    }finally{pending=false;near.disabled=false;near.setAttribute('aria-busy','false');}
  }
  near.addEventListener('click',nearby);route.addEventListener('click',openRoute);
  function cancelNearby(){say();if(!pending)return;version++;mode(trip.open||routing()?'route':'map');}
  trip.addEventListener('toggle',()=>{
    if(trip.open){version++;prepare();say();list.open=false;mode('route');}
    else if(!routing()&&!pending)mode('map');
  });
  window.addEventListener('gas:routechange',()=>{if(routing()){version++;say();mode('route');}else if(!trip.open)mode('map');});
  byId('searchInput').addEventListener('input',()=>{cancelNearby();say();});
  for(const id of ['regionSelect','onnuriMethod','fuelSelect','districtSelect'])byId(id).addEventListener('change',cancelNearby);
  document.querySelectorAll('.filter-btn').forEach(button=>button.addEventListener('click',cancelNearby));
  for(const type of ['pointerdown','touchstart'])document.querySelector('.map-area').addEventListener(type,cancelNearby,{capture:true,passive:true});
  byId('resetBtn').addEventListener('click',()=>{version++;say();mode('map');});
  if(!hasMap){route.disabled=true;near.textContent='목록 보기';}
  mode(trip.open?'route':'map');
})();

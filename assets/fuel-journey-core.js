/* Route contracts; no location collection or request on import. */
(function(root){
  'use strict';
  const point=p=>p&&Number.isFinite(p.lat)&&Number.isFinite(p.lng)&&p.lat>=32&&p.lat<=39&&p.lng>=124&&p.lng<=132;
  function request(origin,station,destination){
    if(!point(origin)||!point(station)||station.route_eligible!==true)throw new Error('출발지 또는 주유소 위치를 확인해 주세요.');
    if(destination&&!point(destination))throw new Error('목적지를 다시 선택해 주세요.');
    const clean=p=>({lat:p.lat,lng:p.lng});
    return {origin:clean(origin),destination:clean(destination||station),...(destination?{waypoint:clean(station)}:{})};
  }
  function route(data){
    if(!data||!Number.isFinite(data.seconds)||data.seconds<0||!Number.isFinite(data.meters)||data.meters<0||!Array.isArray(data.coordinates)||data.coordinates.length<2||data.coordinates.length>100000||!data.coordinates.every(c=>Array.isArray(c)&&point({lng:c[0],lat:c[1]})))throw new Error('경로 응답을 확인하지 못했어요. 다시 조회해 주세요.');
    return data;
  }
  function links(station,appname){
    if(!point(station)||station.route_eligible!==true)throw new Error('길안내에 사용할 위치를 확인하지 못했어요.');
    return {kakao:'https://map.kakao.com/link/to/'+encodeURIComponent(station.name)+','+station.lat+','+station.lng,
      naver:'nmap://route/car?'+new URLSearchParams({dlat:station.lat,dlng:station.lng,dname:station.name,appname})};
  }
  function addedSeconds(base,via){
    route(base);route(via);
    if(base.provider!==via.provider||base.fixture!==via.fixture||via.seconds<base.seconds)return null;
    return via.seconds-base.seconds;
  }
  const api={point,request,route,links,addedSeconds};
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.GasFuelJourneyCore=api;
})(typeof globalThis!=='undefined'?globalThis:this);

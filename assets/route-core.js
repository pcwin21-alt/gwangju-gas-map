(function (root) {
  'use strict';
  const validPoint = p => p && Number.isFinite(p.lat) && Number.isFinite(p.lng) && p.lat >= 31.43 && p.lat <= 44.35 && p.lng >= 122.37 && p.lng <= 132;
  function distance(a, b) {
    const r = Math.PI / 180;
    const h = Math.sin((b.lat-a.lat)*r/2)**2 + Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin((b.lng-a.lng)*r/2)**2;
    return 6371 * 2 * Math.asin(Math.sqrt(h));
  }
  function navigationParams(start, station, destination, appname) {
    if (![start, station, destination].every(validPoint)) throw new Error('경로 좌표가 올바르지 않습니다.');
    return new URLSearchParams({slat: start.lat, slng: start.lng, sname: start.name || '출발지',
      dlat: destination.lat, dlng: destination.lng, dname: destination.name || '목적지',
      v1lat: station.lat, v1lng: station.lng, v1name: station.name, appname}).toString();
  }
  function naverUrl(start, station, destination, android, appname) {
    const query = navigationParams(start, station, destination, appname);
    const fallback = kakaoUrl(start, station, destination);
    return android ? `intent://navigation?${query}#Intent;scheme=nmap;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;package=com.nhn.android.nmap;S.browser_fallback_url=${encodeURIComponent(fallback)};end`
      : `nmap://navigation?${query}`;
  }
  function kakaoUrl(start, station, destination) {
    if (![start, station, destination].every(validPoint)) throw new Error('경로 좌표가 올바르지 않습니다.');
    return 'https://map.kakao.com/link/by/car/' + [start, station, destination].map(p =>
      `${encodeURIComponent(p.name || '출발지')},${p.lat},${p.lng}`).join('/');
  }
  function distanceToRoute(point, coordinates) {
    if(!validPoint(point)||!Array.isArray(coordinates)||coordinates.length<2)return Infinity;
    const scaleX=111.195*Math.cos(point.lat*Math.PI/180),scaleY=111.195;
    let nearest=Infinity;
    for(let i=1;i<coordinates.length;i++) {
      const a=coordinates[i-1],b=coordinates[i];
      if(!validPoint({lng:a?.[0],lat:a?.[1]})||!validPoint({lng:b?.[0],lat:b?.[1]}))return Infinity;
      const ax=(a[0]-point.lng)*scaleX,ay=(a[1]-point.lat)*scaleY,bx=(b[0]-point.lng)*scaleX,by=(b[1]-point.lat)*scaleY;
      const dx=bx-ax,dy=by-ay,den=dx*dx+dy*dy;
      const t=den?Math.max(0,Math.min(1,-(ax*dx+ay*dy)/den)):0;
      nearest=Math.min(nearest,Math.hypot(ax+t*dx,ay+t*dy));
    }
    return nearest;
  }
  function roadRoute(data) {
    const route=data?.routes?.[0],coordinates=route?.geometry?.coordinates;
    if(data?.code!=='Ok'||route?.geometry?.type!=='LineString'||!Array.isArray(coordinates)||coordinates.length<2||
      !coordinates.every(c=>validPoint({lng:c?.[0],lat:c?.[1]}))||!Number.isFinite(route.duration)||route.duration<=0||!Number.isFinite(route.distance)||route.distance<=0)
      throw new Error('자동차 경로를 찾지 못했습니다. 출발지·목적지를 확인하세요.');
    if(data.waypoints?.some(p=>!Number.isFinite(p.distance)||p.distance>500))throw new Error('선택한 장소 가까이에 연결된 자동차 도로가 없습니다. 인근 도로명주소로 다시 선택하세요.');
    return {coordinates,seconds:route.duration,meters:route.distance};
  }
  function shortlist(stations, start, end, scheme, method, fuel = "all", routeOptions = null) {
    const direct = distance(start, end);
    return stations.filter(s => validPoint(s) && s.route_eligible !== false &&
      (!s.verification || (scheme === 'saengsaeng' ? s.verification.saengsaeng?.status === 'confirmed' :
        scheme === 'onnuri' ? ['confirmed','published_snapshot'].includes(s.verification.onnuri?.status) :
        s.verification.saengsaeng?.status === 'confirmed' || ['confirmed','published_snapshot'].includes(s.verification.onnuri?.status))) &&
      (scheme === 'all' || s.payment_types.includes(scheme)) &&
      (fuel === 'all' || s.fuel_kind === fuel) &&
      (scheme !== 'onnuri' || method === 'any' ||
        (method === 'digital' ? s.onnuri_methods?.digital || s.onnuri_methods?.card || s.onnuri_methods?.qr : s.onnuri_methods?.paper)))
      .map(s => ({station: s, corridor:routeOptions?distanceToRoute(s,routeOptions.coordinates):0,penalty: distance(start, s) + distance(s, end) - direct}))
      .filter(row=>!routeOptions||row.corridor<=routeOptions.radiusKm)
      .sort((a,b) => a.corridor-b.corridor||a.penalty-b.penalty).slice(0,routeOptions?Infinity:24).map(x=>x.station);
  }
  function rankMatrix(data, candidates) {
    if (data.code !== 'Ok' || !data.durations || !data.distances) throw new Error('도로 경로를 계산하지 못했습니다.');
    const base = data.durations[0]?.[1];
    if (!Number.isFinite(base) || base <= 0) throw new Error('출발지와 목적지 사이 자동차 경로가 없습니다.');
    return candidates.flatMap((station, i) => {
      const j = i+2, there = data.durations[0]?.[j], onward = data.durations[j]?.[1];
      const snap = data.sources?.[j]?.distance;
      const metersA = data.distances[0]?.[j], metersB = data.distances[j]?.[1], baseMeters = data.distances[0]?.[1];
      if (![there, onward, metersA, metersB, baseMeters].every(Number.isFinite) || !Number.isFinite(snap) || snap > 150) return [];
      return [{station, addedSeconds: Math.max(0, there+onward-base),
        addedMeters: Math.max(0, metersA+metersB-baseMeters), totalSeconds: there+onward}];
    }).sort((a,b) => a.addedSeconds-b.addedSeconds || a.addedMeters-b.addedMeters);
  }
  function matchesRecommendation(row, mode, limit) {
    return Number.isFinite(limit)&&limit>0&&(mode==='distance'?Number.isFinite(row.routeKm)&&row.routeKm<=limit:Number.isFinite(row.addedSeconds)&&row.addedSeconds<limit*60);
  }
  const api = {validPoint, distance, distanceToRoute, roadRoute, matchesRecommendation, navigationParams, naverUrl, kakaoUrl, shortlist, rankMatrix};
  if (typeof module !== 'undefined') module.exports = api;
  root.GasRouteCore = api;
})(typeof window === 'undefined' ? globalThis : window);

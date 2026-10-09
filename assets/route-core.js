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
  function shortlist(stations, start, end, scheme, method, fuel = "all") {
    const direct = distance(start, end);
    return stations.filter(s => validPoint(s) && s.route_eligible !== false &&
      (scheme === 'all' || s.payment_types.includes(scheme)) &&
      (fuel === 'all' || s.fuel_kind === fuel) &&
      (scheme !== 'onnuri' || method === 'any' ||
        (method === 'digital' ? s.onnuri_methods?.card || s.onnuri_methods?.qr : s.onnuri_methods?.paper)))
      .map(s => ({station: s, penalty: distance(start, s) + distance(s, end) - direct}))
      .sort((a,b) => a.penalty-b.penalty).slice(0, 24).map(x=>x.station);
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
  const api = {validPoint, distance, navigationParams, naverUrl, kakaoUrl, shortlist, rankMatrix};
  if (typeof module !== 'undefined') module.exports = api;
  root.GasRouteCore = api;
})(typeof window === 'undefined' ? globalThis : window);

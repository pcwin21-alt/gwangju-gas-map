/* Result ordering and geographic scope never mutate map or filter state. */
(function(root) {
  'use strict';
  const point = p => p && Number.isFinite(p.lat) && Number.isFinite(p.lng);
  function distance(a,b) {
    if(!point(a)||!point(b))return null;
    const r=Math.PI/180,h=Math.sin((b.lat-a.lat)*r/2)**2+Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin((b.lng-a.lng)*r/2)**2;
    return 6371*2*Math.asin(Math.sqrt(Math.min(1,h)));
  }
  function contains(bounds,p) {
    return point(p)&&p.lat>=bounds.south&&p.lat<=bounds.north&&
      (bounds.west<=bounds.east?p.lng>=bounds.west&&p.lng<=bounds.east:p.lng>=bounds.west||p.lng<=bounds.east);
  }
  function select(items,{bounds=null,location=null,order='name'}={}) {
    return items.filter(item=>!bounds||contains(bounds,item.station))
      .map(item=>({item,km:distance(location,item.station)}))
      .sort((a,b)=>{
        if(order==='distance'&&point(location)){
          const delta=(a.km??Infinity)-(b.km??Infinity);if(delta)return delta;
        }
        return String(a.item.station.name).localeCompare(String(b.item.station.name),'ko')||String(a.item.station.id).localeCompare(String(b.item.station.id));
      });
  }
  function distanceText(km) {
    if(!Number.isFinite(km))return '';
    return '내 위치에서 직선 '+(km<1?Math.round(km*1000)+'m':km.toFixed(1)+'km');
  }
  function priceText(station,prices,dates) {
    if(!prices)return '';
    const kinds=station.fuel_kind==='lpg'?['LPG']:['휘발유','경유'];
    const values=kinds.filter(k=>Number.isFinite(prices[k])&&prices[k]>0).map(k=>k+' '+prices[k].toLocaleString('ko-KR')+'원/L');
    if(!values.length)return '';
    const sources=Array.isArray(dates)?dates.filter(d=>typeof d==='string').map(d=>d.replace(/^(\d{4})(\d{2})(\d{2})$/,'$1-$2-$3')):[];
    return values.join(' · ')+' · 유가 '+(sources.join(' / ')||'기준일 미확인');
  }
  const api={distance,contains,select,distanceText,priceText};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.GasStationResults=api;
})(typeof globalThis!=='undefined'?globalThis:this);

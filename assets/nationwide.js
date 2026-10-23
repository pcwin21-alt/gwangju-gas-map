(function(root) {
  'use strict';
  const regions = ['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주'];
  function searchMatches(station, query) {
    const q=(query||'').trim().toLowerCase();
    return !q || [station.name,station.address,...(station.aliases||[])].some(value=>(value||'').toLowerCase().includes(q));
  }
  function matches(station, state) {
    if (state.region !== 'all' && station.region !== state.region) return false;
    if (state.fuel !== 'all' && station.fuel_kind !== state.fuel) return false;
    if (state.method !== 'all') {
      if (!station.payment_types?.includes('onnuri')) return false;
      if (station.onnuri_methods?.[state.method] !== true) return false;
    }
    return true;
  }
  const api={regions,matches,searchMatches};
  if (typeof module==='object' && module.exports) module.exports=api;
  else {root.GasNational=api;root.GasNationalState={region:'all',method:'all',fuel:'all'};}
})(typeof globalThis!=='undefined'?globalThis:this);

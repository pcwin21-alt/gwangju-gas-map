(function(root) {
  'use strict';
  const digital = m => Boolean(m?.digital || m?.card || m?.qr);
  function onnuriNote(station) {
    const v = station.verification?.onnuri;
    if(v?.provider === 'kbcard') return `KB국민카드 조회 ${v.checked_at.slice(0,10)}${v.status === 'confirmed' ? ' · 지류·QR 별도 확인' : ' · 최근 미확인'}`;
    if(v?.status === 'confirmed') return `공식 검색 확인 ${v.checked_at.slice(0,10)}`;
    return v?.status === 'published_snapshot' ? `공식 자료 ${v.source_date}` : `과거 기록 ${v?.checked_at?.slice(0,10) || '미확인'} · 최근 미확인`;
  }
  function verificationText(station) {
    const labels=[];
    if(station.verification?.saengsaeng) labels.push('상생카드 조회: '+station.verification.saengsaeng.checked_at.slice(0,10));
    if(station.payment_types?.includes('onnuri')) labels.push('온누리 '+onnuriNote(station));
    if(station.location_evidence) labels.push('위치: '+(station.location_evidence.source_type==='commercial_registry'?'상권자료 ':'지자체 주유소 자료 ')+(station.location_evidence.source_date||'기준일 미확인'));
    return labels.join(' / ');
  }
  const api = {digital, onnuriNote, verificationText};
  if(typeof module === 'object' && module.exports) module.exports=api;
  else root.GasMerchantDisplay=api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

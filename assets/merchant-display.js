(function(root) {
  'use strict';
  const digital = m => Boolean(m?.digital || m?.card || m?.qr);
  function onnuriNote(station) {
    const v = station.verification?.onnuri;
    return v?.status === 'published_snapshot' ? `공식 자료 ${v.source_date}` : `과거 기록 ${v?.checked_at?.slice(0,10) || '미확인'} · 최근 미확인`;
  }
  function verificationText(station) {
    const labels=[];
    if(station.verification?.saengsaeng) labels.push('상생카드 조회: '+station.verification.saengsaeng.checked_at.slice(0,10));
    if(station.payment_types?.includes('onnuri')) labels.push('온누리 '+onnuriNote(station));
    return labels.join(' / ');
  }
  const api = {digital, onnuriNote, verificationText};
  if(typeof module === 'object' && module.exports) module.exports=api;
  else root.GasMerchantDisplay=api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

(function(root) {
  'use strict';
  const digital = m => Boolean(m?.digital || m?.card || m?.qr);
  const date = value => typeof value==='string'&&/^\d{4}-\d{2}-\d{2}/.test(value)?value.slice(0,10):'미확인';
  function paymentText(station) {
    const labels=[];
    if(station.payment_types?.includes('onnuri')){
      const m=station.onnuri_methods,types=[m?.paper===true&&'지류',digital(m)&&'디지털'].filter(Boolean);
      labels.push('온누리 '+(types.join('·')||'종류 미확인'));
    }
    if(station.payment_types?.includes('saengsaeng'))labels.push('광주상생카드');
    return labels.join(' / ')||'결제 유형 미확인';
  }
  function confirmationText(station) {
    const labels=[],v=station.verification;
    if(station.payment_types?.includes('onnuri'))labels.push(onnuriNote(station));
    if(station.payment_types?.includes('saengsaeng'))labels.push('상생카드 조회 '+date(v?.saengsaeng?.checked_at));
    return labels.join(' / ');
  }
  function onnuriNote(station) {
    const v = station.verification?.onnuri;
    if(v?.provider === 'kbcard') return `KB국민카드 조회 ${date(v.checked_at)}${v.status === 'confirmed' ? ' · 지류·QR 별도 확인' : ' · 최근 미확인'}`;
    if(v?.status === 'confirmed') return `공식 검색 확인 ${date(v.checked_at)}`;
    return v?.status === 'published_snapshot' ? `공식 자료 ${date(v.source_date)}` : `과거 기록 ${date(v?.checked_at)} · 최근 미확인`;
  }
  function verificationText(station) {
    const labels=[];
    if(station.verification?.saengsaeng) labels.push('상생카드 조회: '+date(station.verification.saengsaeng.checked_at));
    if(station.payment_types?.includes('onnuri')) labels.push('온누리 '+onnuriNote(station));
    if(station.location_evidence) labels.push('위치: '+(station.location_evidence.source_type==='commercial_registry'?'상권자료 ':'지자체 주유소 자료 ')+(station.location_evidence.source_date||'기준일 미확인'));
    return labels.join(' / ');
  }
  function paymentSummary(station) {
    if(station.payment_types?.includes('onnuri')&&station.verification?.onnuri?.provider==='kbcard')
      return '온누리 KB국민카드'+(station.payment_types.includes('saengsaeng')?' / 광주상생카드':'');
    return paymentText(station);
  }
  function checkCaption(station) {
    const v=station.payment_types?.includes('onnuri')?station.verification?.onnuri:station.verification?.saengsaeng;
    if(v?.status==='published_snapshot')return date(v.source_date)+' 자료';
    if(!v||v.status!=='confirmed')return '최근 미확인';
    return date(v.checked_at)==='미확인'?'확인일 미확인':date(v.checked_at)+' 확인';
  }
  const api = {digital, onnuriNote, verificationText, paymentText, confirmationText, paymentSummary, checkCaption};
  if(typeof module === 'object' && module.exports) module.exports=api;
  else root.GasMerchantDisplay=api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

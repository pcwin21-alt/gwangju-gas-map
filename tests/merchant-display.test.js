const test=require('node:test');
const assert=require('node:assert/strict');
const display=require('../assets/merchant-display.js');
const core=require('../assets/route-core.js');

test('bank corroboration is labelled by issuer and unknown methods stay unknown',()=>{
 const s={payment_types:['onnuri'],onnuri_methods:{card:true,digital:true,paper:null,qr:null},
 verification:{onnuri:{provider:'kbcard',status:'confirmed',checked_at:'2026-10-26T18:32:23+09:00'}},
 location_evidence:{source_type:'commercial_registry',source_date:'2026-06-30'}};
 assert.match(display.onnuriNote(s),/KB국민카드 조회/);
 assert.match(display.onnuriNote(s),/지류·QR 별도 확인/);
 assert.doesNotMatch(display.onnuriNote(s),/공식 검색 확인/);
 assert.match(display.verificationText(s),/상권자료 2026-06-30/);
 assert.equal(display.paymentSummary(s),'온누리 KB국민카드');
 assert.equal(display.checkCaption(s),'2026-10-26 확인');
});
test('annual data date is separate from retrieval and stale status',()=>{
 const s={payment_types:['onnuri'],verification:{onnuri:{status:'published_snapshot',source_date:'2026-07-31',checked_at:'2026-10-10'}}};
 assert.equal(display.onnuriNote(s),'공식 자료 2026-07-31');
 assert.equal(display.checkCaption(s),'2026-07-31 자료');
 assert.equal(display.checkCaption({payment_types:['onnuri'],verification:{onnuri:{status:'stale',checked_at:'2026-03-03'}}}),'최근 미확인');
 assert.match(display.onnuriNote({verification:{onnuri:{status:'stale',checked_at:'2026-03-03'}}}),/최근 미확인/);
});
test('combined digital support passes route filter without inventing card or QR',()=>{
 const s={name:'주유소',payment_types:['onnuri'],lat:35.18,lng:126.87,route_eligible:true,onnuri_methods:{digital:true,card:false,qr:false,paper:false}};
 assert.equal(display.digital(s.onnuri_methods),true);
 const a={lat:35.16,lng:126.85},b={lat:35.19,lng:126.9};
 assert.equal(core.shortlist([s],a,b,'onnuri','digital').length,1);
 assert.equal(core.shortlist([s],a,b,'onnuri','paper').length,0);
});

test('live official date is shown and verified stops are eligible',()=>{
 const s={name:'함덕주유소',payment_types:['onnuri'],lat:33.54,lng:126.67,route_eligible:true,
   onnuri_methods:{paper:true,card:true,qr:true,digital:true},verification:{onnuri:{status:'confirmed',checked_at:'2026-10-23T23:00:00+09:00'}}};
 assert.equal(display.onnuriNote(s),'공식 검색 확인 2026-10-23');
 assert.equal(core.shortlist([s],{lat:33.5,lng:126.5},{lat:33.55,lng:126.7},'onnuri','digital').length,1);
});

const test=require('node:test');
const assert=require('node:assert/strict');
const display=require('../assets/merchant-display.js');
const core=require('../assets/route-core.js');
test('annual data date is separate from retrieval and stale status',()=>{
 const s={payment_types:['onnuri'],verification:{onnuri:{status:'published_snapshot',source_date:'2026-07-31',checked_at:'2026-10-10'}}};
 assert.equal(display.onnuriNote(s),'공식 자료 2026-07-31');
 assert.match(display.onnuriNote({verification:{onnuri:{status:'stale',checked_at:'2026-03-03'}}}),/최근 미확인/);
});
test('combined digital support passes route filter without inventing card or QR',()=>{
 const s={name:'주유소',payment_types:['onnuri'],lat:35.18,lng:126.87,route_eligible:true,onnuri_methods:{digital:true,card:false,qr:false,paper:false}};
 assert.equal(display.digital(s.onnuri_methods),true);
 const a={lat:35.16,lng:126.85},b={lat:35.19,lng:126.9};
 assert.equal(core.shortlist([s],a,b,'onnuri','digital').length,1);
 assert.equal(core.shortlist([s],a,b,'onnuri','paper').length,0);
});

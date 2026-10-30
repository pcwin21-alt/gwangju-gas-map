const test=require('node:test'),assert=require('node:assert/strict');
const core=require('../assets/station-results-core.js'),display=require('../assets/merchant-display.js');
const item=(id,name,lat,lng)=>({station:{id,name,lat,lng}});

test('distance ordering uses the actual location, retains all results and leaves source order untouched',()=>{
 const rows=[item('far','가 주유소',35.2,126.9),item('near','나 주유소',35,126),item('missing','다 주유소',null,null)];
 const ordered=core.select(rows,{location:{lat:35,lng:126},order:'distance'});
 assert.deepEqual(ordered.map(r=>r.item.station.id),['near','far','missing']);
 assert.deepEqual(rows.map(r=>r.station.id),['far','near','missing']);
 assert.equal(ordered[0].km,0);assert.equal(ordered[2].km,null);
 assert.match(core.distanceText(ordered[1].km),/^내 위치에서 직선 [\d.]+km$/);
 assert.equal(core.distanceText(null),'');
});
test('without permission distance ordering falls back to names without inventing a default location',()=>{
 const rows=[item('b','나',35,126),item('a','가',35,127)];
 const ordered=core.select(rows,{order:'distance'});
 assert.deepEqual(ordered.map(r=>r.item.station.id),['a','b']);assert.ok(ordered.every(r=>r.km===null));
});
test('a captured map scope is inclusive and does not change when the source list changes',()=>{
 const bounds={south:35,north:35.2,west:126,east:126.2};
 const rows=[item('edge','경계',35,126),item('inside','내부',35.1,126.1),item('outside','외부',35.3,126.1),item('missing','미확인',null,null)];
 assert.deepEqual(core.select(rows,{bounds}).map(r=>r.item.station.id).sort(),['edge','inside']);
 assert.deepEqual(bounds,{south:35,north:35.2,west:126,east:126.2});
 assert.equal(core.select(rows,{bounds:{south:34,north:34.1,west:125,east:125.1}}).length,0);
});
test('only positive known prices for the station fuel appear, with a readable source date',()=>{
 const prices={휘발유:1800,경유:null,LPG:990};
 assert.equal(core.priceText({fuel_kind:'liquid'},prices,['20261030']),'휘발유 1,800원/L · 유가 2026-10-30');
 assert.equal(core.priceText({fuel_kind:'lpg'},prices,['2026-10-29']),'LPG 990원/L · 유가 2026-10-29');
 assert.equal(core.priceText({fuel_kind:'liquid'},{휘발유:0,경유:'1800'}), '');
 assert.equal(core.priceText({fuel_kind:'liquid'},null), '');
 assert.match(core.priceText({fuel_kind:'liquid'},{휘발유:1800}),/기준일 미확인$/);
});
test('list payment labels retain both schemes and do not turn unknown methods into support',()=>{
 assert.equal(display.paymentText({payment_types:['onnuri','saengsaeng'],onnuri_methods:{paper:true,digital:true}}),'온누리 지류·디지털 / 광주상생카드');
 assert.equal(display.paymentText({payment_types:['onnuri'],onnuri_methods:{paper:null,digital:null}}),'온누리 종류 미확인');
 assert.equal(display.paymentText({payment_types:[]}),'결제 유형 미확인');
});
test('missing check dates remain unverified and supplemental card evidence retains its issuer limit',()=>{
 const station={payment_types:['onnuri'],verification:{onnuri:{provider:'kbcard',status:'confirmed'}}};
 assert.match(display.confirmationText(station),/KB국민카드 조회 미확인 · 지류·QR 별도 확인/);
 assert.doesNotMatch(display.confirmationText(station),/공식 검색 확인/);
});

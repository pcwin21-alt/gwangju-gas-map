const test=require('node:test');const assert=require('node:assert/strict');
const {matches}=require('../assets/nationwide.js');
const station={region:'경기',fuel_kind:'liquid',payment_types:['onnuri'],onnuri_methods:{paper:true,digital:false}};
test('paper-only merchant cannot leak into digital or LPG results',()=>{
 assert.equal(matches(station,{region:'경기',fuel:'all',method:'digital'}),false);
 assert.equal(matches(station,{region:'경기',fuel:'lpg',method:'paper'}),false);
 assert.equal(matches(station,{region:'경기',fuel:'liquid',method:'paper'}),true);
 assert.equal(matches(station,{region:'광주',fuel:'all',method:'all'}),false);
});
test('unknown methods are not treated as supported',()=>{
 assert.equal(matches({...station,onnuri_methods:{paper:null}},{region:'all',fuel:'all',method:'paper'}),false);
});
test('stale Onnuri records cannot become a recommended fuel stop',()=>{
 const {shortlist}=require('../assets/route-core.js');
 const s={...station,lat:35.2,lng:126.9,verification:{onnuri:{status:'stale'}}};
 assert.deepEqual(shortlist([s],{lat:35,lng:126.8},{lat:35.4,lng:127},'onnuri','any'),[]);
});

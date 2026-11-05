const {test}=require('node:test');const assert=require('node:assert/strict');
const core=require('../assets/fuel-journey-core.js');
const origin={lat:35.15,lng:126.9,name:'공개 출발지'},station={lat:35.14,lng:126.91,name:'A&B 주유소',route_eligible:true},end={lat:35.16,lng:126.92};
test('transmits only needed coordinates; optional final destination is not silently lost',()=>{
 const payload=core.request(origin,station,end);assert.deepEqual(payload,{origin:{lat:35.15,lng:126.9},destination:end,waypoint:{lat:35.14,lng:126.91}});assert.ok(!JSON.stringify(payload).includes('공개'));
 assert.throws(()=>core.request(origin,{...station,route_eligible:false}));assert.throws(()=>core.request({lat:NaN,lng:126},station));
});
test('missing geometry and nonfinite estimates cannot become a zero-minute route',()=>{
 assert.throws(()=>core.route({seconds:0,meters:0,coordinates:[]}));assert.throws(()=>core.route({seconds:NaN,meters:1,coordinates:[[126,35],[126,35]]}));
});
test('negative/mismatched extra time is unknown; exact zero remains a valid comparison',()=>{
 const route={seconds:400,meters:3000,coordinates:[[126.9,35.15],[126.91,35.14]],provider:'test',fixture:false};
 assert.equal(core.addedSeconds(route,{...route,seconds:399}),null);assert.equal(core.addedSeconds(route,{...route,provider:'other'}),null);assert.equal(core.addedSeconds(route,{...route}),0);
});
test('navigation names are escaped and no user origin or store fallback is sent',()=>{
 const urls=core.links(station,'https://example.test');assert.ok(urls.kakao.includes('A%26B'));assert.ok(!JSON.stringify(urls).includes('market:'));assert.ok(!urls.naver.includes('slat='));assert.throws(()=>core.links({...station,lat:0},'test'));
});

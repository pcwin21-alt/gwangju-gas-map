const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../assets/route-core.js');
const start={lat:35.16,lng:126.85,name:'출발지'},end={lat:35.19,lng:126.9,name:'최종 목적지'};
const station={lat:35.18,lng:126.87,name:'주유소 & 지점',payment_types:['onnuri'],onnuri_methods:{paper:true,card:false,qr:false},route_eligible:true};
test('final destination and waypoint transmitted separately',()=>{
 const params=new URLSearchParams(core.navigationParams(start,station,end,'test'));
 assert.equal(params.get('dname'),'최종 목적지');assert.equal(params.get('v1name'),station.name);
 assert.equal(params.get('v1lat'),'35.18');assert.ok(core.kakaoUrl(start,station,end).includes(encodeURIComponent(station.name)));
 assert.match(core.naverUrl(start,station,end,true,'test'),/intent:\/\/navigation/);
});
test('digital excludes paper-only and invalid coordinates',()=>{
 assert.equal(core.shortlist([station],start,end,'onnuri','digital').length,0);
 assert.equal(core.shortlist([station],start,end,'onnuri','paper').length,1);
 assert.equal(core.shortlist([{...station,lat:null}],start,end,'all','any').length,0);
});
test('no route or distant road snap never reported as zero detour',()=>{
 const d={code:'Ok',durations:[[0,600,300],[600,0,300],[300,400,0]],distances:[[0,5000,3000],[5000,0,3000],[3000,3000,0]],sources:[{distance:0},{distance:0},{distance:10}]};
 assert.equal(core.rankMatrix(d,[station])[0].addedSeconds,100);
 d.durations[2][1]=null;assert.deepEqual(core.rankMatrix(d,[station]),[]);
 d.durations[2][1]=400;d.sources[2].distance=200;assert.deepEqual(core.rankMatrix(d,[station]),[]);
});
test('bad final destination rejected',()=>assert.throws(()=>core.navigationParams(start,station,{lat:NaN,lng:1},'test')));

test('corridor follows a bent road rather than the direct start-end line and does not truncate 24 matches',()=>{
 const coordinates=[[126.85,35.16],[126.85,35.5],[127.2,35.5],[127.2,35.16]];
 const onRoad={...station,lat:35.5,lng:127.0},between={...station,lat:35.16,lng:127.0};
 assert.ok(core.distanceToRoute(onRoad,coordinates)<.001);
 assert.ok(core.distanceToRoute(between,coordinates)>10);
 const rows=Array.from({length:30},(_,id)=>({...onRoad,id}));
 const shortlist=core.shortlist([...rows,between],start,end,'onnuri','paper','all',{coordinates,radiusKm:1});
 assert.equal(shortlist.length,30);assert.ok(!shortlist.includes(between));
 assert.equal(core.distanceToRoute(onRoad,[]),Infinity);
});

test('5 minutes is strictly less than 300 seconds; radius is inclusive; missing estimates never qualify',()=>{
 assert.equal(core.matchesRecommendation({addedSeconds:299.9},'time',5),true);
 assert.equal(core.matchesRecommendation({addedSeconds:300},'time',5),false);
 assert.equal(core.matchesRecommendation({routeKm:2},'distance',2),true);
 assert.equal(core.matchesRecommendation({routeKm:2.001},'distance',2),false);
 assert.equal(core.matchesRecommendation({},'time',5),false);
});

test('route geometry, duration and road snap must be valid before showing a driving route',()=>{
 const response={code:'Ok',routes:[{duration:600,distance:5000,geometry:{type:'LineString',coordinates:[[126.85,35.16],[126.9,35.19]]}}],waypoints:[{distance:2},{distance:4}]};
 assert.equal(core.roadRoute(response).seconds,600);
 response.waypoints[1].distance=501;assert.throws(()=>core.roadRoute(response),/자동차 도로/);
 response.waypoints[1].distance=4;response.routes[0].geometry.coordinates[1][0]=null;assert.throws(()=>core.roadRoute(response));
});

const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('output/map.html','utf8');

function fixture(){
  const gestures={},sdkEvents=new Map(),changes=[],map={};
  const host={hidden:true,firstElementChild:null,replaceChildren(content){changes.push(content?.id||'closed');this.firstElementChild=content||null;},querySelector(){return {focus(){}};}};
  const context={STATIONS:[{id:'a',lat:35,lng:126,address:'광주 북구'},{id:'b',lat:35.1,lng:126.1,address:'광주 남구'}],
    map,window:{},markerImages:{onnuri:{}},getMarkerType:()=> 'onnuri',buildInfoHtml:s=>s,
    document:{activeElement:null,getElementById:id=>id==='stationDetails'?host:{open:true},querySelector:()=>({addEventListener:(name,fn)=>gestures[name]=fn})},
    kakao:{maps:{LatLng:class{},Marker:class{},event:{addListener(target,name,fn){if(!sdkEvents.has(target))sdkEvents.set(target,{});sdkEvents.get(target)[name]=fn;}}}},
    searchFitTimer:1,clearTimeout(){},mapViewport:{cancelFit(){}}
  };
  vm.createContext(context);
  vm.runInContext(html.slice(html.indexOf('// 마커 생성'),html.indexOf('// 필터 + 검색 적용')),context);
  vm.runInContext(html.slice(html.indexOf('// A later direct gesture'),html.indexOf('function updateStationSearch(')),context);
  const rows=vm.runInContext('allMarkers',context);
  return {host,changes,rows,context,gestures,click:i=>sdkEvents.get(rows[i].marker).click(),drag:()=>sdkEvents.get(map).dragstart(),
    gesture:name=>gestures[name]({target:{closest:()=>null}})};
}

test('duplicate SDK clicks select the same station without closing, remounting or refocusing it',()=>{
  const f=fixture();f.click(0);f.click(0);
  assert.equal(f.host.hidden,false);assert.equal(f.host.firstElementChild.id,'a');
  assert.deepEqual(f.changes,['a']);
});

test('a hybrid touch/pointer sequence cannot dismiss the station it just selected',()=>{
  const f=fixture();f.gesture('pointerdown');f.click(0);f.gesture('touchstart');f.click(0);
  assert.equal(f.host.hidden,false);assert.deepEqual(f.changes,['a']);
});

test('selecting a different pin changes the card once and does not fit, center or zoom the map',()=>{
  const f=fixture();f.click(0);f.click(1);f.click(1);
  assert.equal(f.host.firstElementChild.id,'b');assert.equal(f.host.hidden,false);
  assert.deepEqual(f.changes,['a','closed','b']);
});

test('actual map dragging dismisses details; a touch down alone leaves them readable',()=>{
  const f=fixture();f.click(0);f.gesture('pointerdown');f.gesture('touchstart');
  assert.equal(f.host.hidden,false);f.drag();assert.equal(f.host.hidden,true);
});

test('report mode ignores station selection',()=>{
  const f=fixture();vm.runInContext('reportMode=true',f.context);f.click(0);
  assert.equal(f.host.hidden,true);assert.deepEqual(f.changes,[]);
});

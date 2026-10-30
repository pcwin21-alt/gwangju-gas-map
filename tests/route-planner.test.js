const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const core = require('../assets/route-core.js');

function setup(options={}) {
  const html = fs.readFileSync('output/map.html','utf8');
  class Element {
    constructor() {this.value='';this.textContent='';this.children=[];this.listeners={};this.classList={add(){},remove(){}};}
    addEventListener(type,fn) {(this.listeners[type] ||= []).push(fn);}
    async emit(type,extra={}) {for(const fn of this.listeners[type]||[]) await fn({preventDefault(){},...extra});}
    replaceChildren(...nodes) {this.children=nodes;}
    append(node) {this.children.push(node);}
    focus() {}
    blur() {}
    setAttribute() {}
  }
  const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
  const el = id => {assert.ok(elements[id],`Missing HTML element: ${id}`);return elements[id];};
  for (const match of html.matchAll(/<select id="([^"]+)"[^>]*>\s*<option value="([^"]+)"/g)) el(match[1]).value=match[2];
  const lookups=[], gps=[],roads=[],draws=[];
  let now=10000;
  const sandbox={GasRouteCore:core, document:{getElementById:el,querySelector:()=>({dataset:{filter:'all'}}),createElement:()=>new Element()},
    window:{GasRouteMap:{clear(){draws.push(null);},show(...args){draws.push(args);},fit(){}}}, MERCHANT_STATUS:{}, STATIONS:options.stations||[], PRICES:{},
    GasMerchantDisplay:{digital:m=>m.digital,onnuriNote:()=>'',verificationText:()=>''},
    navigator:{userAgent:''},location:{hostname:'example.test'},Date:{now:()=>now+=2000},setTimeout,clearTimeout,AbortController,DOMException,
    fetch:async url=>{roads.push(url);return {ok:true,json:async()=>options.road?options.road(url):{code:'Error'}};},
    kakao:{maps:{services:{Status:{OK:'OK'},Places:class{keywordSearch(q,cb){lookups.push({q,cb});}}}}},
    locateUser:()=>new Promise((resolve,reject)=>gps.push({resolve,reject}))};
  vm.runInNewContext(fs.readFileSync('assets/route-planner.js','utf8'),sandbox);
  async function selectDestination() {
    el('tripDestination').value='목포역';await el('tripForm').emit('submit');
    lookups.at(-1).cb([{place_name:'목포역',y:'34.791',x:'126.386',address_name:'전남 목포시'}],'OK');
    await el('tripChoices').children[0].emit('click');
  }
  async function selectStart() {
    el('tripStart').value='광주송정역';await el('tripSearchStart').emit('click');
    lookups.at(-1).cb([{place_name:'광주송정역',y:'35.138',x:'126.791',address_name:'광주'}],'OK');
    await el('tripChoices').children[0].emit('click');
  }
  return {el,lookups,gps,roads,draws,selectDestination,selectStart,chooseStation:sandbox.window.GasRoutePlanner.chooseStation};
}

test('destination search and selection never request GPS; button advances and editing invalidates it',async()=>{
  const {el,gps,selectDestination}=setup();
  await selectDestination();
  assert.equal(gps.length,0);
  assert.equal(el('tripRecommend').textContent,'경유 주유소 찾기');
  el('tripDestination').value='다른 장소';await el('tripDestination').emit('input');
  assert.equal(el('tripRecommend').textContent,'목적지 검색');
});
test('Korean composition Enter never submits a place search',async()=>{
  const {el,lookups}=setup();el('tripDestination').value='목포';
  await el('tripDestination').emit('keydown',{key:'Enter',isComposing:true});
  await el('tripDestination').emit('keydown',{key:'Enter',keyCode:229});
  assert.equal(lookups.length,0);
});
test('route defaults include all payment methods; first-open filters are retained on reopen',async()=>{
  const {el}=setup();
  el('tripPanel').open=true;await el('tripPanel').emit('toggle');
  assert.equal(el('tripPayment').value,'all');assert.equal(el('tripMethod').value,'any');
  assert.equal(el('tripMethod').disabled,true);
  el('tripPayment').value='onnuri';await el('tripPayment').emit('change');
  el('tripMethod').value='paper';await el('tripMethod').emit('change');
  await el('tripPanel').emit('toggle');
  assert.equal(el('tripMethod').value,'paper');
  assert.match(el('tripSettingsSummary').textContent,/온누리 · 지류/);
});
test('location denial reveals manual start entry without losing the selected destination',async()=>{
  const {el,gps,selectDestination}=setup();await selectDestination();
  const pending=el('tripForm').emit('submit');
  assert.equal(gps.length,1);gps[0].reject(new Error('위치 권한을 허용하거나 출발지를 직접 검색하세요.'));
  await pending;
  assert.equal(el('tripSettings').open,true);assert.equal(el('tripRecommend').disabled,false);
  assert.equal(el('tripRecommend').textContent,'경유 주유소 찾기');
});
test('editing destination while GPS is pending cancels the old request',async()=>{
  const {el,gps,selectDestination}=setup();await selectDestination();
  const pending=el('tripForm').emit('submit');
  el('tripDestination').value='다른 목적지';await el('tripDestination').emit('input');
  gps[0].resolve({lat:35.16,lng:126.85});await pending;
  assert.equal(el('tripStart').value,'');
  assert.equal(el('tripRecommend').textContent,'목적지 검색');
  assert.match(el('tripStatus').textContent,/취소/);
});

test('selected endpoints automatically draw the road and list only stations strictly below 5-minute detour',async()=>{
 const s={id:'one',name:'경로 주유소',lat:35,lng:126.6,payment_types:['onnuri'],fuel_kind:'liquid',route_eligible:true};
 const f=setup({stations:[s],road:url=>url.includes('/route/')?{code:'Ok',routes:[{duration:600,distance:5000,geometry:{type:'LineString',coordinates:[[126.791,35.138],[126.6,35],[126.386,34.791]]}}]}:{code:'Ok',durations:[[0,600,300],[600,0,300],[300,400,0]],distances:[[0,5000,3000],[5000,0,3000],[3000,3000,0]],sources:[{distance:0},{distance:0},{distance:2}]}});
 await f.selectStart();assert.equal(f.roads.length,0);await f.selectDestination();
 assert.equal(f.gps.length,0);assert.equal(f.roads.length,2);assert.ok(f.roads[0].includes('/route/'));
 assert.equal(f.draws.filter(Boolean).at(-1)[3][0].id,'one');
 assert.equal(f.el('tripResults').children.length,1);assert.match(f.el('tripStatus').textContent,/推薦|추천 1곳/);
 assert.match(f.el('tripRouteSummary').textContent,/광주송정역.*목포역.*5.0km/);
 await f.el('tripClear').emit('click');assert.equal(f.draws.at(-1),null);assert.equal(f.el('tripResults').children.length,0);
});

test('no matching stations still leaves the actual road visible and changeable',async()=>{
 const f=setup({road:()=>({code:'Ok',routes:[{duration:600,distance:5000,geometry:{type:'LineString',coordinates:[[126.791,35.138],[126.386,34.791]]}}]})});
 await f.selectStart();await f.selectDestination();
 assert.ok(f.draws.some(Boolean));assert.equal(f.el('tripShowMap').hidden,false);assert.match(f.el('tripStatus').textContent,/조건에 맞는 주유소가 없습니다/);
 assert.equal(f.el('tripRefresh').disabled,false);
});
test('a late start-place response cannot replace newer destination choices',async()=>{
 const f=setup();f.el('tripStart').value='광주송정역';await f.el('tripSearchStart').emit('click');const old=f.lookups.at(-1);
 f.el('tripDestination').value='목포역';await f.el('tripForm').emit('submit');const latest=f.lookups.at(-1);
 latest.cb([{place_name:'목포역',y:'34.791',x:'126.386',address_name:'전남'}],'OK');
 old.cb([{place_name:'광주송정역',y:'35.138',x:'126.791',address_name:'광주'}],'OK');
 assert.match(f.el('tripChoices').children[0].textContent,/목포역/);
});
test('manual start edits while location is pending cannot be overwritten by the old GPS',async()=>{
 const f=setup();const pending=f.el('tripLocation').emit('click');assert.equal(f.el('tripLocation').disabled,true);
 f.el('tripStart').value='직접 고른 출발지';await f.el('tripStart').emit('input');
 f.gps[0].resolve({lat:35.16,lng:126.85});await pending;
 assert.equal(f.el('tripStart').value,'직접 고른 출발지');assert.equal(f.el('tripLocation').disabled,false);
});
test('repeated compare submissions while waiting for a start make only one location request',async()=>{
 const f=setup();await f.selectDestination();const pending=f.el('tripForm').emit('submit');await f.el('tripForm').emit('submit');assert.equal(f.gps.length,1);
 f.gps[0].reject(new Error('denied'));await pending;assert.equal(f.el('tripRecommend').disabled,false);
});
test('a station chosen before the destination is remembered through manual endpoint selection',async()=>{
 const f=setup(),station={id:'chosen',name:'선택한 주유소',address:'주소',lat:35,lng:126.6,payment_types:['onnuri'],route_eligible:true};
 await f.chooseStation(station);assert.equal(f.gps.length,0);assert.match(f.el('tripStatus').textContent,/선택한 주유소/);
 await f.selectDestination();assert.equal(f.el('tripRecommend').textContent,'이 주유소로 경유 연결');
 await f.selectStart();assert.equal(f.roads.length,0);assert.equal(f.el('tripResults').children.length,1);assert.match(f.el('tripStatus').textContent,/선택한 주유소/);
 await f.el('tripClear').emit('click');assert.equal(f.el('tripRecommend').textContent,'경유 주유소 찾기');
});

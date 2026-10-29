const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const core = require('../assets/route-core.js');

function setup() {
  const html = fs.readFileSync('output/map.html','utf8');
  class Element {
    constructor() {this.value='';this.textContent='';this.children=[];this.listeners={};this.classList={add(){},remove(){}};}
    addEventListener(type,fn) {(this.listeners[type] ||= []).push(fn);}
    async emit(type,extra={}) {for(const fn of this.listeners[type]||[]) await fn({preventDefault(){},...extra});}
    replaceChildren(...nodes) {this.children=nodes;}
    append(node) {this.children.push(node);}
    focus() {}
  }
  const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
  const el = id => {assert.ok(elements[id],`Missing HTML element: ${id}`);return elements[id];};
  for (const match of html.matchAll(/<select id="([^"]+)"[^>]*>\s*<option value="([^"]+)"/g)) el(match[1]).value=match[2];
  const lookups=[], gps=[];
  const sandbox={GasRouteCore:core, document:{getElementById:el,querySelector:()=>({dataset:{filter:'all'}}),createElement:()=>new Element()},
    window:{}, MERCHANT_STATUS:{}, STATIONS:[], setTimeout,clearTimeout,AbortController,DOMException,
    kakao:{maps:{services:{Status:{OK:'OK'},Places:class{keywordSearch(q,cb){lookups.push({q,cb});}}}}},
    locateUser:()=>new Promise((resolve,reject)=>gps.push({resolve,reject}))};
  vm.runInNewContext(fs.readFileSync('assets/route-planner.js','utf8'),sandbox);
  async function selectDestination() {
    el('tripDestination').value='목포역';await el('tripForm').emit('submit');
    lookups.at(-1).cb([{place_name:'목포역',y:'34.791',x:'126.386',address_name:'전남 목포시'}],'OK');
    await el('tripChoices').children[0].emit('click');
  }
  return {el,lookups,gps,selectDestination};
}

test('destination search and selection never request GPS; button advances and editing invalidates it',async()=>{
  const {el,gps,selectDestination}=setup();
  await selectDestination();
  assert.equal(gps.length,0);
  assert.equal(el('tripRecommend').textContent,'경유 주유소 찾기');
  el('tripDestination').value='다른 장소';await el('tripDestination').emit('input');
  assert.equal(el('tripRecommend').textContent,'목적지 검색');
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

const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const core=require('../assets/station-results-core.js'),national=require('../assets/nationwide.js'),display=require('../assets/merchant-display.js');

function fixture({fallback=false,count=25}={}) {
 const nodes={},events={},mapEvents={};let sandbox,bounds={south:34,north:36,west:125,east:128},fits=0,moves=0,route=false;
 const document={activeElement:null,getElementById:id=>el(id),querySelector:selector=>selector==='.map-area'?el('area'):buttons.find(b=>b.classList.contains('active')),querySelectorAll:()=>buttons,createElement:()=>new Element()};
 class Element {
  constructor(){this.children=[];this.listeners={};this.dataset={};this.attributes={};this.style={setProperty(){}};this.scrollTop=0;this.value='';this.clientHeight=640;this.isConnected=true;const classes=new Set();this.classList={contains:k=>classes.has(k),toggle(k,v){if(v)classes.add(k);else classes.delete(k);}};}
  get options(){return this.children;}
  add(value){this.children.push(value);}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attributes[k]=v;}
  addEventListener(type,fn){(this.listeners[type]||=[]).push(fn);}
  emit(type,extra={}){for(const fn of this.listeners[type]||[])fn({preventDefault(){},stopPropagation(){},...extra});}
  dispatchEvent(event){this.emit(event.type);}
  querySelector(selector){if(selector==='summary')return el('summary');if(selector.includes('distance'))return el('distanceOption');if(selector.includes('map'))return el('mapOption');return null;}
  getBoundingClientRect(){return {height:52};}
  focus(){document.activeElement=this;}
 }
 function el(id){return nodes[id]||=(new Element());}
 const buttons=['all','onnuri','saengsaeng'].map(filter=>{const n=new Element();n.dataset.filter=filter;return n;});
 for(const [id,value] of Object.entries({regionSelect:'광주',onnuriMethod:'all',fuelSelect:'all',resultsScope:'region',resultsOrder:'name'}))el(id).value=value;
 el('nationalResults').dataset.size='half';
 const stations=Array.from({length:count},(_,i)=>({id:String(i),name:'주유소 '+String(i).padStart(2,'0'),address:'광주 북구 '+i,region:'광주',lat:35+i*.01,lng:126,payment_types:['onnuri'],onnuri_methods:{paper:true},fuel_kind:'liquid'}));
 const window={addEventListener(type,fn){(events[type]||=[]).push(fn);},GasRouteMap:{isActive:()=>route}};
 sandbox={document,window,GasStationResults:core,GasNational:national,GasNationalState:{region:'all',fuel:'all',method:'all'},GasMerchantDisplay:display,MERCHANT_STATUS:{},STATIONS:stations,NATIONAL_PENDING:[],PRICES:{},
  currentLocation:null,currentFilter:'all',currentDistrict:'all',allMarkers:stations.map(station=>({station,visible:true,overlay:{}})),
  Option:class{constructor(label,value){this.textContent=label;this.value=value;}},URL,location:{href:'https://example.test/?region=광주&payment=onnuri'},history:{replaceState(){},pushState(){}},
  ResizeObserver:class{observe(){}},clearRankMapOverlays(){},setDistrictHighlight(){},triggerDistrictSelect(){},mapViewport:{fit(){fits++;}},
  applyFilters(){for(const item of sandbox.allMarkers)item.visible=national.matches(item.station,sandbox.GasNationalState)&&item.station.payment_types.includes(sandbox.currentFilter);},
  showStationOverlay(overlay,options){window.GasResultsPanel.onDetailsOpen(options.fromResults);el('nationalResults').open=false;},
  map:{getBounds:()=>({getSouthWest:()=>({getLat:()=>bounds.south,getLng:()=>bounds.west}),getNorthEast:()=>({getLat:()=>bounds.north,getLng:()=>bounds.east})}),setCenter(){moves++;},setLevel(){moves++;}},
  kakao:fallback?undefined:{maps:{LatLng:class{constructor(lat,lng){this.lat=lat;this.lng=lng;}},event:{addListener:(map,name,fn)=>(mapEvents[name]||=[]).push(fn)}}}
 };
 window.kakao=sandbox.kakao;
 if(fallback)Object.defineProperty(sandbox,'currentLocation',{get(){throw new Error('uninitialized map state');}});
 vm.runInNewContext(fs.readFileSync('assets/nationwide-ui.js','utf8'),sandbox);
 return {el,stations,sandbox,window,setBounds:value=>bounds=value,emitMap:type=>{for(const fn of mapEvents[type]||[])fn();},emitWindow:type=>{for(const fn of events[type]||[])fn();},fits:()=>fits,moves:()=>moves,setRoute:value=>route=value};
}
test('search this area captures a scope without fitting the map, while later map idle only updates the count',()=>{
 const f=fixture(),fits=f.fits(),moves=f.moves();
 f.setBounds({south:35,north:35.011,west:125.9,east:126.1});f.emitMap('dragend');
 assert.equal(f.el('searchAreaBtn').hidden,false);f.el('searchAreaBtn').emit('click');
 assert.equal(f.el('resultsScope').value,'map');assert.equal(f.el('stationList').children.length,2);assert.equal(f.fits(),fits);assert.equal(f.moves(),moves);
 f.el('resultsBody').scrollTop=80;
 f.setBounds({south:34,north:34.1,west:125,east:125.1});f.emitMap('idle');
 assert.equal(f.el('stationList').children.length,2);assert.equal(f.el('resultsBody').scrollTop,80);assert.match(f.el('listScope').textContent,/현재 지도 안 0곳/);
 f.el('searchAreaBtn').emit('click');assert.match(f.el('stationList').children[0].textContent,/없습니다/);
 const actions=f.el('stationList').children[1];assert.ok(actions.children.some(b=>b.textContent==='선택 지역 전체 보기'));
 actions.children.find(b=>b.textContent==='선택 지역 전체 보기').emit('click');assert.equal(f.el('stationList').children.length,20);
});
test('more results, close and reopen preserve the selected row and list scroll without new map movement',()=>{
 const f=fixture();f.el('resultsBody').scrollTop=140;f.el('moreStations').emit('click');
 assert.equal(f.el('stationList').children.length,25);assert.equal(f.el('resultsBody').scrollTop,140);
 const row=f.el('stationList').children[22];row.emit('click');const moves=f.moves();
 assert.equal(f.el('nationalResults').open,false);assert.equal(f.window.GasResultsPanel.restoreSelection(),true);
 assert.equal(f.el('nationalResults').open,true);assert.equal(f.el('resultsBody').scrollTop,140);assert.equal(f.sandbox.document.activeElement,row);assert.equal(f.moves(),moves);
 f.window.GasResultsPanel.onDetailsOpen(false);assert.equal(f.window.GasResultsPanel.restoreSelection(),false);
 f.el('resultsSize').emit('click');assert.equal(f.el('nationalResults').dataset.size,'full');f.el('resultsSize').emit('click');assert.equal(f.el('nationalResults').dataset.size,'half');
});
test('location enables actual distance ordering, and future location changes respect a manually chosen order',()=>{
 const f=fixture();assert.equal(f.el('distanceOption').disabled,true);
 f.sandbox.currentLocation={lat:35.24,lng:126};f.emitWindow('gas:locationchange');
 assert.equal(f.el('distanceOption').disabled,false);assert.equal(f.el('resultsOrder').value,'distance');assert.equal(f.el('stationList').children[0].dataset.stationId,'24');
 f.el('resultsOrder').value='name';f.el('resultsOrder').emit('change');f.emitWindow('gas:locationchange');
 assert.equal(f.el('resultsOrder').value,'name');assert.equal(f.el('stationList').children[0].dataset.stationId,'0');
});
test('fallback can filter and paginate even when map globals never initialized',()=>{
 const f=fixture({fallback:true});assert.equal(f.el('mapOption').disabled,true);assert.equal(f.el('stationList').children.length,20);
 assert.equal(f.el('stationList').children[0].target,'_blank');assert.equal(f.el('tripPanel').hidden,true);
 f.el('moreStations').emit('click');assert.equal(f.el('stationList').children.length,25);
 f.el('searchInput').value='주유소 24';f.el('searchInput').emit('input');assert.equal(f.el('stationList').children.length,1);
 assert.match(f.el('listCount').textContent,/1곳/);
});

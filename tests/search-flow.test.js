const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture({fallback=false}={}){
 const nodes={},events={},gps=[],moves=[];let active=false,listed=0,closed=0;
 const node=id=>nodes[id]||=( {hidden:false,open:false,value:'',attributes:{},handlers:{},textContent:'',disabled:false,
  addEventListener(k,fn){(this.handlers[k]||=[]).push(fn);},setAttribute(k,v){this.attributes[k]=v;},
  async emit(k){for(const fn of this.handlers[k]||[])await fn();},querySelector:()=>node('summary'),focus(){document.activeElement=this;}} );
 const document={activeElement:null,getElementById:node,querySelector:()=>node('area'),querySelectorAll:()=>[node('payment')]};
 const window={kakao:fallback?undefined:{maps:{LatLng:class{constructor(lat,lng){this.lat=lat;this.lng=lng;}}}},
  addEventListener:(k,fn)=>(events[k]||=[]).push(fn),GasRouteMap:{isActive:()=>active},
  GasTripWindow:{open(){node('tripPanel').open=true;node('tripPanel').emit('toggle');},minimize(){node('tripPanel').open=false;}},
  GasResultsPanel:{showNearby(){listed++;node('nationalResults').open=true;}},
  GasRoutePlanner:{clearForMapSearch(){active=false;(events['gas:routechange']||[]).forEach(fn=>fn());}}};
 vm.runInNewContext(fs.readFileSync('assets/search-flow.js','utf8'),{window,document,closeStationOverlay(){closed++;},
  map:{setCenter:p=>moves.push(p),setLevel:v=>moves.push(v)},locateUser:options=>new Promise((resolve,reject)=>gps.push({options,resolve,reject}))});
 return {node,document,window,gps,moves,listed:()=>listed,closed:()=>closed,setRoute:v=>active=v};
}
test('load and route entry never request GPS; route entry closes competing panels and retains inputs',async()=>{
 const f=fixture();assert.equal(f.gps.length,0);f.node('tripDestination').value='목포역';f.node('mapFilters').hidden=false;f.node('nationalResults').open=true;
 await f.node('routeModeBtn').emit('click');assert.equal(f.gps.length,0);assert.equal(f.node('tripPanel').open,true);
 assert.equal(f.node('mapFilters').hidden,true);assert.equal(f.node('nationalResults').open,false);assert.equal(f.node('tripDestination').value,'목포역');
 assert.equal(f.node('routeModeBtn').attributes['aria-pressed'],'true');assert.ok(f.closed()>0);
});
test('nearby waits for an explicit location result, prevents duplicate requests and opens nearest results',async()=>{
 const f=fixture();const pending=f.node('nearbyModeBtn').emit('click');await f.node('nearbyModeBtn').emit('click');
 assert.equal(f.gps.length,1);assert.equal(f.gps[0].options.center,false);assert.equal(f.node('nearbyModeBtn').disabled,true);
 f.gps[0].resolve({lat:35,lng:126});await pending;
 assert.equal(f.listed(),1);assert.equal(f.moves.length,2);assert.equal(f.node('nearbyModeBtn').disabled,false);
 assert.equal(f.node('nearbyModeBtn').attributes['aria-pressed'],'true');assert.equal(f.node('searchFlowStatus').hidden,true);
});
test('a late location response cannot steal the route screen or move the map',async()=>{
 const f=fixture();const pending=f.node('nearbyModeBtn').emit('click');await f.node('routeModeBtn').emit('click');
 f.gps[0].resolve({lat:35,lng:126});await pending;
 assert.equal(f.listed(),0);assert.equal(f.moves.length,0);assert.equal(f.node('tripPanel').open,true);
 assert.equal(f.node('routeModeBtn').attributes['aria-pressed'],'true');
});
test('map manipulation or a filter change takes precedence over a pending nearby lookup',async()=>{
 for(const [id,event] of [['area','pointerdown'],['area','touchstart'],['regionSelect','change'],['payment','click']]){
  const f=fixture(),pending=f.node('nearbyModeBtn').emit('click');await f.node(id).emit(event);
  f.gps[0].resolve({lat:35,lng:126});await pending;assert.equal(f.listed(),0);assert.equal(f.moves.length,0);
 }
});
test('permission failure offers manual search without clearing the query and remains retryable',async()=>{
 const f=fixture();f.node('searchInput').value='돌고개';const pending=f.node('nearbyModeBtn').emit('click');f.gps[0].reject(Error('denied'));await pending;
 assert.match(f.node('searchFlowStatus').textContent,/주소로 검색/);assert.equal(f.node('searchInput').value,'돌고개');assert.equal(f.node('nearbyModeBtn').disabled,false);
 await f.node('regionSelect').emit('change');assert.equal(f.node('searchFlowStatus').hidden,true);
});
test('SDK fallback offers the address list and disables unavailable routing without requesting location',async()=>{
 const f=fixture({fallback:true});assert.equal(f.node('routeModeBtn').disabled,true);assert.equal(f.node('nearbyModeBtn').textContent,'목록 보기');
 await f.node('nearbyModeBtn').emit('click');assert.equal(f.gps.length,0);assert.equal(f.node('nationalResults').open,true);assert.equal(f.closed(),0);
});
test('filter, region and explicit search entry minimize the route window without losing its inputs',async()=>{
 for(const [id,event] of [['filtersToggle','click'],['regionOpen','click'],['searchInput','focus']]){
  const f=fixture();await f.node('routeModeBtn').emit('click');f.node('tripDestination').value='목포역';
  f.node('mapFilters').hidden=false;await f.node(id).emit(event);
  assert.equal(f.node('tripPanel').open,false);assert.equal(f.node('tripDestination').value,'목포역');
  assert.equal(f.node('mapFilters').hidden,false);assert.equal(f.gps.length,0);
 }
});

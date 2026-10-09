const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function fixture(points){
 const calls=[],jobs=new Map();let next=0,resize;
 const context={requestAnimationFrame:fn=>{jobs.set(++next,fn);return next;},cancelAnimationFrame:id=>jobs.delete(id),ResizeObserver:class{constructor(fn){resize=fn;}observe(){}}};
 vm.runInNewContext(fs.readFileSync(require.resolve('../assets/map-viewport.js'),'utf8'),context);
 const sdk={LatLng:class{constructor(lat,lng){this.lat=lat;this.lng=lng;}},LatLngBounds:class{constructor(){this.points=[];}extend(p){this.points.push(p);}}};
 const center={lat:35.18,lng:126.87};
 const map={relayout:()=>calls.push(['relayout']),getCenter:()=>center,setCenter:p=>calls.push(['center',p]),setLevel:l=>calls.push(['level',l]),setBounds:(...args)=>calls.push(['bounds',...args])};
 const container={clientWidth:390,clientHeight:400};
 const api=context.GasMapViewport.create(map,container,()=>points,sdk);
 const flush=()=>{while(jobs.size){const list=[...jobs.values()];jobs.clear();list.forEach(fn=>fn());}};
 return {api,calls,container,flush,resize:()=>resize(),center};
}
test('region fit includes all valid filtered locations with padding inside a short map',()=>{
 const f=fixture([{lat:35.1,lng:126.8},{lat:35.2,lng:126.9},{lat:NaN,lng:126.8}]);
 f.container.clientHeight=120;f.api.fit();f.flush();
 const bounds=f.calls.find(c=>c[0]==='bounds');
 assert.equal(bounds[1].points.length,2);
 assert.ok(bounds[2]+bounds[4]<120);
});
test('empty results keep map unchanged and a single result gets useful zoom',()=>{
 const empty=fixture([]);empty.api.fit();empty.flush();assert.equal(empty.calls.length,0);
 const one=fixture([{lat:35.1,lng:126.8}]);one.api.fit();one.flush();
 assert.equal(one.calls.find(c=>c[0]==='level')[1],4);
 assert.equal(one.calls.some(c=>c[0]==='bounds'),false);
});
test('height resize preserves current view while width resize refits the selected results',()=>{
 const f=fixture([{lat:35.1,lng:126.8},{lat:35.2,lng:126.9}]);
 f.container.clientHeight=250;f.resize();f.flush();
 assert.equal(f.calls.find(c=>c[0]==='center')[1],f.center);
 assert.equal(f.calls.some(c=>c[0]==='bounds'),false);
 f.container.clientWidth=800;f.resize();f.flush();
 assert.equal(f.calls.some(c=>c[0]==='bounds'),true);
});

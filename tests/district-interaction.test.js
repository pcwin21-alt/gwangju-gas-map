const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('output/map.html','utf8');
function fixture(){
 const polygons=[],select={value:'all',listeners:{},addEventListener(name,fn){this.listeners[name]=fn;}};
 let zoom=3,center='user-panned-center',filters=0,highlight,closed=0;
 const context={window:{},map:{},currentDistrict:'all',districtPolygonMap:{},DISTRICT_COLORS:{'동구':'orange','서구':'green','남구':'cyan','북구':'purple','광산구':'red'},document:{querySelectorAll:()=>[],querySelector:()=>null,getElementById:id=>{assert.equal(id,'districtSelect');return select;}},applyFilters(){filters++;},setDistrictHighlight:name=>highlight=name,clearRankMapOverlays(){},activeOverlay:{setMap(value){assert.equal(value,null);closed++;}},mapViewport:{fit(){zoom=8;center='filtered-results';}}};
 context.kakao={maps:{LatLng:function(lat,lng){this.lat=lat;this.lng=lng;},Polygon:function(options){this.options=options;this.events={};polygons.push(this);},event:{addListener:(target,name,fn)=>target.events[name]=fn}}};
 vm.createContext(context);
 const start=html.indexOf('function triggerDistrictSelect(');
 vm.runInContext(html.slice(start,html.indexOf('// 내 위치',start)),context);
 vm.runInContext(html.match(/\(function\(\)\s*\{\s*var GJ = [\s\S]*?\}\)\(\);/)[0],context);
 return {context,polygons,select,state:()=>({zoom,center,filters,highlight,closed})};
}
test('clicks anywhere on Gwangju boundaries preserve the user zoom, center and station filters',()=>{
 const f=fixture();assert.equal(f.polygons.length,5);
 for(const polygon of f.polygons)polygon.events.click?.();
 assert.deepEqual(f.state(),{zoom:3,center:'user-panned-center',filters:0,highlight:undefined,closed:0});
 assert.equal(f.context.currentDistrict,'all');assert.equal(f.select.value,'all');
 assert.ok(f.polygons.every(p=>p.options.map===f.context.map&&p.options.path.length>3));
});
test('explicit district menu selection still filters and fits results',()=>{
 const f=fixture();f.select.value='남구';f.select.listeners.change.call(f.select);
 assert.equal(f.context.currentDistrict,'남구');assert.equal(f.select.value,'남구');
 assert.deepEqual(f.state(),{zoom:8,center:'filtered-results',filters:1,highlight:'남구',closed:1});
});

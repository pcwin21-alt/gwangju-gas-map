const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const core=require('../assets/district-context-core.js');
const rectangle=(x1,y1,x2,y2)=>[[[[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]]]];
const features=[{name:'west',polygons:rectangle(-1000,-1000,210,2000)},{name:'east',polygons:rectangle(210,-1000,2000,2000)}];
test('shared border identifies the center side and places both labels within their own visible areas',()=>{
 const result=core.context(features,390,600);
 assert.equal(result.home,'west');assert.deepEqual(result.neighbors,['east']);assert.equal(result.labels.length,2);
 for(const label of result.labels){assert.ok(core.contains(label.point,features.find(f=>f.name===label.name).polygons));assert.ok(label.point[0]>=42&&label.point[0]<=348);}
 const moved=features.map(f=>({...f,polygons:f.polygons.map(rings=>rings.map(ring=>ring.map(([x,y])=>[x-40,y])))}));
 assert.equal(core.context(moved,390,600).home,'east');
});
test('far from boundaries or outside Gwangju no misleading center district is shown',()=>{
 assert.deepEqual(core.context([{name:'inside',polygons:rectangle(-1000,-1000,2000,2000)}],390,600),{home:null,neighbors:[],labels:[]});
 const nearby=core.context([{name:'edge',polygons:rectangle(210,-1000,2000,2000)}],390,600);
 assert.equal(nearby.home,null);assert.deepEqual(nearby.neighbors,['edge']);
 assert.equal(core.context([{name:'far',polygons:rectangle(1000,1000,2000,2000)}],390,600).labels.length,0);
});
test('holes, disconnected polygons and narrow visible slivers cannot receive invalid labels',()=>{
 const polygon=rectangle(0,0,390,600);polygon[0].push(rectangle(100,100,290,500)[0][0]);
 assert.equal(core.contains([195,300],polygon),false);assert.equal(core.contains([50,300],polygon),true);
 const islands=[...rectangle(0,0,100,600),...rectangle(290,0,390,600)];
 assert.equal(core.contains([330,300],islands),true);assert.equal(core.contains([195,300],islands),false);
 assert.equal(core.anchor(rectangle(190,0,210,600),390,600),null);
 const p=core.anchor(polygon,390,600);assert.ok(p);assert.equal(core.contains(p,polygon),true);
});
test('map idle refreshes labels while drag and wide zoom hide them without location or network services',()=>{
 const elements={districtContext:{hidden:true},districtContextName:{},districtContextNear:{}},events={},overlays=[];
 let level=4,pending,resize;
 const maps={LatLng:function(y,x){this.x=x;this.y=y;},Point:function(x,y){this.x=x;this.y=y;},CustomOverlay:function(options){this.options=options;this.setMap=m=>this.map=m;this.setPosition=p=>this.position=p;overlays.push(this);},event:{addListener:(m,name,fn)=>events[name]=fn}};
 const map={getLevel:()=>level,getCenter:()=>({}),getProjection:()=>({containerPointFromCoords:p=>p,coordsFromContainerPoint:p=>p})};
 const context={window:{kakao:{maps},GasDistrictGeoJSON:{features:features.map(f=>({properties:{gu:f.name},geometry:{type:'MultiPolygon',coordinates:f.polygons}}))}},kakao:{maps},GasDistrictContextCore:core,DISTRICT_COLORS:{},map,document:{querySelector:()=>({clientWidth:390,clientHeight:600}),getElementById:id=>elements[id],createElement:()=>({style:{setProperty(){}}})},requestAnimationFrame:fn=>(pending=fn,1),cancelAnimationFrame(){},ResizeObserver:function(fn){resize=fn;this.observe=()=>{};}};
 vm.runInNewContext(fs.readFileSync('assets/district-context.js','utf8'),context);pending();
 assert.equal(elements.districtContext.hidden,false);assert.match(elements.districtContextName.textContent,/west/);assert.equal(overlays.filter(o=>o.map===map).length,2);
 events.dragstart();assert.equal(elements.districtContext.hidden,true);assert.equal(overlays.filter(o=>o.map).length,0);
 events.idle();pending();assert.equal(elements.districtContext.hidden,false);
 level=9;events.zoom_start();events.idle();pending();assert.equal(elements.districtContext.hidden,true);
 level=4;resize();pending();assert.equal(elements.districtContext.hidden,false);
});

const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('route map draws the full road, numbered candidates and endpoints; clear removes private session geometry',()=>{
 const overlays=[],bounds=[];let changes=0;
 class Overlay {constructor(options){this.options=options;overlays.push(this);}setMap(value){this.map=value;}}
 const maps={Polyline:Overlay,CustomOverlay:Overlay,LatLng:class{constructor(lat,lng){this.lat=lat;this.lng=lng;}},LatLngBounds:class{constructor(){this.points=[];}extend(p){this.points.push(p);}}};
 const window={kakao:{maps},dispatchEvent(){changes++;}},normalMarker={setMap(value){this.map=value;}},baseMap={setBounds:b=>bounds.push(b)};
 vm.runInNewContext(fs.readFileSync('assets/route-map.js','utf8'),{window,kakao:{maps},CustomEvent:class{},map:baseMap,allMarkers:[{marker:normalMarker,visible:true}],document:{createElement:()=>({setAttribute(){},addEventListener(){}})}});
 const route={coordinates:[[126.85,35.16],[126.87,35.18],[126.9,35.19]]};
 window.GasRouteMap.show(route,{lat:35.16,lng:126.85,name:'출발'},{lat:35.19,lng:126.9,name:'도착'},[{id:'s1',lat:35.18,lng:126.87,name:'확인 주유소'}]);
 const features=window.GasRouteMap.collection().features;
 assert.equal(features.length,4);assert.equal(features[0].geometry.coordinates.length,3);assert.equal(features[3].properties.label,'1');
 assert.equal(bounds.at(-1).points.length,6);assert.equal(overlays.length,5);assert.equal(window.GasRouteMap.isActive(),true);
 assert.equal(normalMarker.map,null);
 window.GasRouteMap.clear();assert.equal(window.GasRouteMap.collection().features.length,0);assert.ok(overlays.every(o=>o.map===null));assert.ok(changes>=2);
 assert.equal(normalMarker.map,baseMap);
});

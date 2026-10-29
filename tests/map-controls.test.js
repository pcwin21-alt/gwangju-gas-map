const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(withVector=false) {
  const html=fs.readFileSync('output/map.html','utf8'),elements={},requests=[],docListeners={},windowListeners={};
  function node(){const classes=new Set();return {listeners:{},style:{},classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x),toggle(x,on){on?classes.add(x):classes.delete(x);}},attributes:{},setAttribute(k,v){this.attributes[k]=v;},addEventListener(type,fn){this.listeners[type]=fn;},remove(){},async emit(type,event={}){await this.listeners[type]?.(event);}};}
  for(const match of html.matchAll(/id="([^"]+)"/g))elements[match[1]]=node();
  elements.area=node();elements.app=node();
  const byId=id=>{assert.ok(elements[id],`Missing HTML control ${id}`);return elements[id];};
  const document={documentElement:{dataset:{theme:'light'}},getElementById:byId,querySelector:s=>elements[s==='.app'?'app':'area'],createElement:node,head:{append:el=>requests.push(el)},addEventListener:(k,v)=>docListeners[k]=v};
  let level=8;
  const point={getLat:()=>35.16,getLng:()=>126.85};
  const map={setCenter(){},getCenter:()=>point,setLevel:value=>level=value,setBounds(){},getLevel:()=>level};
  let rendered;
  class Vector {
    constructor(options){this.sources={};this.handlers={};this.styleURL=options.style;rendered=this;}
    once(type,fn){if(type==='load')queueMicrotask(fn);}
    off(){} on(type,fn){this.handlers[type]=fn;} addLayer(){} resize(){} jumpTo(){} getBearing(){return 0;}
    setStyle(url){this.styleURL=url;this.sources={};this.handlers['style.load']?.();}
    addSource(id,source){this.sources[id]={data:source.data,setData(data){this.data=data;}};}
    getSource(id){return this.sources[id];}
  }
  const gl={Map:Vector};
  const rows=[{visible:true,markerType:'onnuri',station:{id:'one',name:'확인 주유소',lat:35.16,lng:126.85}},{visible:false,station:{id:'hidden'}}];
  const context={window:{addEventListener:(k,v)=>windowListeners[k]=v,kakao:{maps:{}},matchMedia:()=>({matches:true}),maplibregl:withVector?gl:null},maplibregl:gl,map,document,setTimeout,clearTimeout,queueMicrotask,ResizeObserver:class{observe(){}},COLOR:{onnuri:'#f59e0b'},allMarkers:rows,console:{warn(){}},applyFilters(){},showStationOverlay(){},setCurrentLocation(){}};
  vm.runInNewContext(fs.readFileSync('assets/map-controls.js','utf8'),context);
  return {elements,requests,docListeners,windowListeners,level:()=>level,rendered:()=>rendered,rows,context,document};
}
test('default map remains usable and does not fetch the rotation bundle until requested',async()=>{
  const f=fixture();assert.equal(f.requests.length,0);
  await f.elements.mapZoomIn.emit('click');assert.equal(f.level(),7);
  await f.elements.mapZoomOut.emit('click');assert.equal(f.level(),8);
});
test('expanded map retains a reachable exit and Escape restores the app controls',async()=>{
  const f=fixture();await f.elements.expandMapBtn.emit('click');
  assert.equal(f.elements.app.classList.contains('map-expanded'),true);
  assert.equal(f.elements.expandMapBtn.attributes['aria-pressed'],'true');
  f.docListeners.keydown({key:'Escape'});
  assert.equal(f.elements.app.classList.contains('map-expanded'),false);
});
test('rotation bundle failure leaves the original map active and the control retryable',async()=>{
  const f=fixture(),pending=f.elements.rotationBtn.emit('click');
  assert.equal(f.requests.length,2);f.requests[1].onerror();await pending;
  assert.equal(f.elements.area.classList.contains('vector-active'),false);
  assert.equal(f.elements.rotationBtn.disabled,false);
  assert.match(f.elements.mapModeStatus.textContent,/다시/);
});
test('loaded rotation mode shows only filtered stations and follows later filter changes',async()=>{
  const f=fixture(true);await f.elements.rotationBtn.emit('click');
  assert.equal(f.elements.area.classList.contains('vector-active'),true);
  const source=f.rendered().getSource('stations');assert.equal(source.data.features.length,1);
  assert.equal(source.data.features[0].properties.color,'#f59e0b');
  f.rows[0].visible=false;f.context.applyFilters();assert.equal(source.data.features.length,0);
});
test('light/dark style switches keep the filtered station layer',async()=>{
  const f=fixture(true);await f.elements.rotationBtn.emit('click');
  f.document.documentElement.dataset.theme='dark';await f.windowListeners['gas:themechange']();
  assert.match(f.rendered().styleURL,/\/dark$/);assert.equal(f.rendered().getSource('stations').data.features.length,1);
  f.document.documentElement.dataset.theme='light';await f.windowListeners['gas:themechange']();
  assert.match(f.rendered().styleURL,/\/liberty$/);assert.equal(f.rendered().getSource('stations').data.features.length,1);
});

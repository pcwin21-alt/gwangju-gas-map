const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(ready=true) {
 const html=fs.readFileSync('output/map.html','utf8'),elements={},docListeners={},windowListeners={};
 function node(){const classes=new Set();return {listeners:{},classList:{contains:x=>classes.has(x),toggle(x,on){on?classes.add(x):classes.delete(x);}},attributes:{},setAttribute(k,v){this.attributes[k]=v;},addEventListener(type,fn){this.listeners[type]=fn;},emit(type,event={}){this.listeners[type]?.(event);}};}
 for(const match of html.matchAll(/id="([^"]+)"/g))elements[match[1]]=node();elements.area=node();elements.app=node();
 let level=8,filters=0,refreshes=0,active=false;
 const byId=id=>{assert.ok(elements[id],`Missing HTML control ${id}`);return elements[id];};
 const document={documentElement:{dataset:{theme:'dark'}},getElementById:byId,querySelector:s=>elements[s==='.app'?'app':'area'],addEventListener:(k,v)=>docListeners[k]=v};
 const context={window:{addEventListener:(k,v)=>windowListeners[k]=v,kakao:ready?{maps:{}}:null,GasRouteMap:{refresh(){refreshes++;},isActive:()=>active}},document,map:{getLevel:()=>level,setLevel:v=>level=v},applyFilters(){filters++;}};
 vm.runInNewContext(fs.readFileSync('assets/map-controls.js','utf8'),context);
 return {elements,docListeners,windowListeners,context,level:()=>level,filters:()=>filters,refreshes:()=>refreshes,setActive:v=>active=v};
}
test('single Kakao map retains bounded zoom; dark theme has no second map or rotation switch',()=>{
 const f=fixture();f.elements.mapZoomIn.emit('click');assert.equal(f.level(),7);f.elements.mapZoomOut.emit('click');assert.equal(f.level(),8);
 for(let i=0;i<20;i++)f.elements.mapZoomOut.emit('click');assert.equal(f.level(),14);
 assert.equal(f.elements.rotationMap,undefined);assert.equal(f.elements.rotationBtn,undefined);assert.equal(f.elements.plainMapBtn,undefined);
 assert.equal(f.windowListeners['gas:themechange'],undefined);
});
test('expanded map retains a reachable exit and Escape restores the app controls',()=>{
 const f=fixture();f.elements.expandMapBtn.emit('click');assert.equal(f.elements.app.classList.contains('map-expanded'),true);
 assert.equal(f.elements.expandMapBtn.attributes['aria-pressed'],'true');f.docListeners.keydown({key:'Escape'});assert.equal(f.elements.app.classList.contains('map-expanded'),false);
});
test('filter changes keep the single-map route markers separate and clear restores the regular view',()=>{
 const f=fixture();f.context.applyFilters();assert.equal(f.filters(),1);assert.equal(f.refreshes(),1);
 f.setActive(true);f.windowListeners['gas:routechange']();assert.equal(f.elements.area.classList.contains('trip-route-active'),true);
 f.setActive(false);f.windowListeners['gas:routechange']();assert.equal(f.elements.area.classList.contains('trip-route-active'),false);
});
test('missing Kakao SDK keeps zoom controls disabled without loading an alternative engine',()=>{
 const f=fixture(false);assert.equal(f.elements.mapZoomIn.disabled,true);assert.equal(f.elements.mapZoomOut.disabled,true);
});

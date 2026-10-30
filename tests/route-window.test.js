const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function fixture() {
 const elements={},listeners={},saved={};let observer;
 const document={activeElement:null,documentElement:{classList:{contains:()=>false}},getElementById:id=>el(id),querySelector:()=>el('area'),addEventListener:(type,fn)=>listeners[type]=fn};
 function el(id){return elements[id] ||= {open:false,value:id==='tripOpacity'?'1':'',hidden:false,attributes:{},styles:{},style:{setProperty(k,v){el(id).styles[k]=v;}},handlers:{},addEventListener(type,fn){this.handlers[type]=fn;},setAttribute(k,v){this.attributes[k]=v;},contains(node){return node?.parent===this;},querySelector:()=>el('summary'),querySelectorAll(){return this.rows||[];},focus(){document.activeElement=this;},blur(){document.activeElement=null;}};}
 const window={innerHeight:844,addEventListener:(type,fn)=>listeners['window:'+type]=fn};el('area').clientHeight=650;
 vm.runInNewContext(fs.readFileSync('assets/route-window.js','utf8'),{window,document,ResizeObserver:class{observe(){}},localStorage:{getItem:k=>saved[k],setItem:(k,v)=>saved[k]=v},getComputedStyle:()=>({getPropertyValue:()=> '#111d2e'}),MutationObserver:class{constructor(fn){observer=fn;}observe(){}}});
 return {el,document,window,listeners,saved,observe:()=>observer()};
}
test('map gesture minimizes without cancelling pan; reopening preserves inputs and results and never focuses a text field',()=>{
 const f=fixture(),panel=f.el('tripPanel');f.el('tripDestination').value='목포역';f.el('tripResults').rows=[{name:'확인 주유소'}];
 f.el('tripLauncher').handlers.click();assert.equal(panel.open,true);assert.equal(f.document.activeElement,f.el('summary'));
 const input=f.el('tripDestination');input.parent=panel;f.document.activeElement=input;
 f.el('area').handlers.pointerdown({target:{closest:()=>null},preventDefault(){assert.fail('pan cancelled');}});
 assert.equal(panel.open,false);assert.equal(f.document.activeElement,null);assert.equal(input.value,'목포역');
 f.el('tripLauncher').handlers.click();assert.equal(panel.open,true);assert.equal(f.el('tripResults').rows.length,1);
});
test('popup touches keep it open; touch-only gesture and Escape offer reachable minimize/reopen',()=>{
 const f=fixture();f.window.GasTripWindow.open();f.el('area').handlers.pointerdown({target:{closest:()=>f.el('tripPanel')}});assert.equal(f.el('tripPanel').open,true);
 f.el('area').handlers.touchstart({target:{closest:()=>null}});assert.equal(f.el('tripPanel').open,false);
 f.window.GasTripWindow.open();f.listeners.keydown({key:'Escape'});assert.equal(f.document.activeElement,f.el('tripLauncher'));
});
test('transparency changes only the background, survives storage and retains a result count on the launcher',()=>{
 const f=fixture();f.el('tripOpacity').value='0.75';f.el('tripOpacity').handlers.change();
 assert.equal(f.el('tripPanel').styles['--trip-surface'],'rgba(17,29,46,0.75)');assert.equal(f.el('tripPanel').styles.opacity,undefined);assert.equal(f.saved['gas-trip-opacity'],'0.75');
 f.el('tripResults').rows=[{},{}];f.observe();assert.equal(f.el('tripLauncherCount').textContent,'2');assert.match(f.el('tripLauncher').attributes['aria-label'],/추천 2곳/);
});

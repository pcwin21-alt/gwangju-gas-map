const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function fixture() {
  const listeners={},elements={};
  const node=id=>elements[id] ||= {open:true,addEventListener:(type,fn)=>{listeners[id+':'+type]=fn;},contains:el=>el?.panel===id};
  const attrs={},classes=new Set();
  const document={activeElement:null,addEventListener:(type,fn)=>{listeners['doc:'+type]=fn;},getElementById:node,querySelector:()=>node('map'),
    documentElement:{style:{setProperty:(k,v)=>attrs[k]=v},classList:{toggle:(k,on)=>on?classes.add(k):classes.delete(k)}}};
  const viewport={height:800,scale:1,addEventListener:(type,fn)=>listeners['viewport:'+type]=fn};
  const window={PointerEvent:class{},innerHeight:800,innerWidth:390,visualViewport:viewport,addEventListener:(type,fn)=>listeners['window:'+type]=fn};
  vm.runInNewContext(fs.readFileSync('assets/input-ux.js','utf8'),{document,window,requestAnimationFrame:fn=>fn()});
  const input={matches:()=>true,blur(){document.activeElement=null;},panel:'tripPanel'};
  return {document,window,viewport,input,classes,attrs,elements,listeners};
}
test('map pointer gesture dismisses editing without cancelling the original gesture',()=>{
  const f=fixture();f.document.activeElement=f.input;
  f.listeners['map:pointerdown']({target:{closest:()=>null},preventDefault(){assert.fail('map gesture cancelled');}});
  assert.equal(f.document.activeElement,null);
});
test('touching an overlay input keeps editing focus; clicking an action dismisses it',()=>{
  const f=fixture();f.document.activeElement=f.input;
  f.listeners['map:pointerdown']({target:{closest:()=>f.input}});
  assert.equal(f.document.activeElement,f.input);
  f.listeners['doc:click']({target:{closest:()=>({id:'tripRecommend'})}});
  assert.equal(f.document.activeElement,null);
});
test('viewport shrinks around keyboard without focusing input and preserves pinch zoom',()=>{
  const f=fixture();f.document.activeElement=f.input;f.viewport.height=450;f.listeners['viewport:resize']();
  assert.equal(f.attrs['--app-height'],'450px');assert.equal(f.classes.has('keyboard-open'),true);
  f.viewport.scale=2;f.viewport.height=225;f.listeners['viewport:resize']();
  assert.equal(f.attrs['--app-height'],'450px');
});
test('collapsing a panel releases its hidden input; IME Enter stays in the field',()=>{
  const f=fixture();f.document.activeElement=f.input;f.elements.tripPanel.open=false;f.listeners['tripPanel:toggle']();
  assert.equal(f.document.activeElement,null);f.document.activeElement=f.input;
  f.listeners['searchInput:keydown']({key:'Enter',isComposing:true});assert.equal(f.document.activeElement,f.input);
  f.listeners['searchInput:keydown']({key:'Enter',preventDefault(){}});assert.equal(f.document.activeElement,null);
});

test('WebView touch fallback covers both maps even when PointerEvent is declared',()=>{
 const f=fixture();f.document.activeElement=f.input;
 f.listeners['map:touchstart']({target:{closest:()=>null},preventDefault(){assert.fail('native touch cancelled');}});
 assert.equal(f.document.activeElement,null);
});

test('WebView resizing both viewports still detects keyboard; read-only clipboard fields do not count as editing',()=>{
 const f=fixture();f.document.activeElement=f.input;f.window.innerHeight=450;f.viewport.height=450;f.listeners['window:resize']();
 assert.equal(f.classes.has('keyboard-open'),true);assert.equal(f.attrs['--app-height'],'450px');
 f.input.readOnly=true;f.listeners['doc:focusin']();assert.equal(f.classes.has('keyboard-open'),false);
});

test('viewport pan reveals a field inside a modal without refocusing or blurring it',()=>{
 const f=fixture(),scroller={scrollTop:0,getBoundingClientRect:()=>({top:50,bottom:800})};
 f.input.closest=()=>scroller;f.input.getBoundingClientRect=()=>({top:600,bottom:650});
 f.document.activeElement=f.input;f.viewport.height=400;f.viewport.offsetTop=50;
 f.listeners['viewport:scroll']();assert.equal(scroller.scrollTop,212);assert.equal(f.document.activeElement,f.input);
});

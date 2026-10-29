const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(saved=null,dark=false,storageBlocked=false) {
  const handlers={},system={},select={value:'',addEventListener:(key,fn)=>handlers['select:'+key]=fn},meta={setAttribute(key,val){this[key]=val;}},events=[];
  const query={matches:dark,addEventListener:(key,fn)=>system[key]=fn};
  const root={dataset:{},style:{}};
  const context={document:{documentElement:root,querySelector:()=>meta,getElementById:()=>select,addEventListener:(key,fn)=>handlers[key]=fn},window:{matchMedia:()=>query,dispatchEvent:event=>events.push(event),addEventListener:(key,fn)=>handlers['window:'+key]=fn},localStorage:{getItem(){if(storageBlocked)throw Error('blocked');return saved;},setItem(key,val){if(storageBlocked)throw Error('blocked');saved=val;}},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options.detail;}}};
  vm.runInNewContext(fs.readFileSync('assets/theme.js','utf8'),context);
  handlers.DOMContentLoaded();
  return {root,handlers,query,system,select,events,saved:()=>saved};
}
test('system theme applies before form setup and follows OS changes',()=>{
  const f=fixture(null,true);assert.equal(f.root.dataset.theme,'dark');assert.equal(f.select.value,'system');
  f.query.matches=false;f.system.change();assert.equal(f.root.dataset.theme,'light');
});
test('manual choice persists and is not overwritten by OS preference',()=>{
  const f=fixture();f.select.value='dark';f.handlers['select:change']();assert.equal(f.saved(),'dark');
  f.query.matches=false;f.system.change();assert.equal(f.root.dataset.theme,'dark');
  assert.equal(fixture(f.saved()).root.dataset.theme,'dark');
});
test('blocked storage and invalid saved values fall back to system without breaking UI',()=>{
  const f=fixture('nonsense',true,true);assert.equal(f.root.dataset.theme,'dark');
  f.select.value='light';assert.doesNotThrow(()=>f.handlers['select:change']());assert.equal(f.root.dataset.theme,'light');
  assert.equal(fixture('nonsense').select.value,'system');
});
test('theme tokens keep body and button text above 4.5:1 contrast',()=>{
  const css=fs.readFileSync('assets/theme.css','utf8');
  const luminance=hex=>{const values=hex.match(/\w\w/g).map(h=>parseInt(h,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return values[0]*.2126+values[1]*.7152+values[2]*.0722;};
  const tokens={};
  for(const block of [css.match(/:root \{([^}]+)\}/)[1],css.match(/:root\[data-theme="dark"\] \{([^}]+)\}/)[1]]) {
    for(const match of block.matchAll(/--([\w-]+):#([\da-f]{6})/g))tokens[match[1]]=match[2];
    for(const [fg,bg] of [['ink','panel'],['muted','panel'],['muted','field'],['on-primary','primary']]) {
      const a=luminance(tokens[fg]),b=luminance(tokens[bg]);assert.ok((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5,`${fg} on ${bg}`);
    }
  }
});

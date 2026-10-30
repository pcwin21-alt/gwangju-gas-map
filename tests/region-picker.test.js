const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const national=require('../assets/nationwide.js');
test('first visit opens Gwangju while explicit nationwide and province links retain their scope',()=>{
 for(const value of [null,'','unknown'])assert.equal(national.regionFromURL(value),'광주');
 assert.equal(national.regionFromURL('all'),'all');
 for(const region of national.regions)assert.equal(national.regionFromURL(region),region);
});
function fixture(initial='광주') {
 const elements={},windowEvents={};let changes=0;
 const node=()=>({listeners:{},attributes:{},dataset:{},children:[],addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);},emit(name,event={}){for(const fn of this.listeners[name]||[])fn(event);},dispatchEvent(event){this.emit(event.type,event);},setAttribute(k,v){this.attributes[k]=v;},append(child){this.children.push(child);},focus(){this.focused=true;}});
 for(const id of ['regionSelect','regionDialog','regionOpen','regionLabel','regionClose','regionOptions','resetBtn'])elements[id]=node();
 const input=elements.regionSelect,dialog=elements.regionDialog;input.value=initial;input.addEventListener('change',()=>changes++);
 dialog.showModal=()=>dialog.open=true;dialog.close=()=>{dialog.open=false;dialog.emit('close');};dialog.getBoundingClientRect=()=>({left:20,right:370,top:100,bottom:600});
 const context={document:{getElementById:id=>elements[id],createElement:node},GasNational:national,window:{addEventListener:(name,fn)=>windowEvents[name]=fn},Event:class{constructor(type,options){this.type=type;Object.assign(this,options);}}};
 vm.runInNewContext(fs.readFileSync('assets/region-picker.js','utf8'),context);
 const button=value=>elements.regionOptions.children.find(b=>b.dataset.region===value);
 return {elements,dialog,input,button,windowEvents,changes:()=>changes};
}
test('popup selects a region once through the existing filter event and restores launcher focus',()=>{
 const f=fixture();f.elements.regionOpen.emit('click');assert.equal(f.dialog.open,true);assert.equal(f.button('광주').focused,true);
 f.button('전남').emit('click');assert.equal(f.input.value,'전남');assert.equal(f.changes(),1);assert.equal(f.dialog.open,false);
 assert.equal(f.elements.regionLabel.textContent,'전남');assert.equal(f.elements.regionOpen.focused,true);assert.equal(f.button('전남').attributes['aria-pressed'],'true');
});
test('opening, dismissing, and reselecting the current region cannot refit or alter filters',()=>{
 const f=fixture();f.elements.regionOpen.emit('click');f.elements.regionClose.emit('click');assert.equal(f.changes(),0);
 f.elements.regionOpen.emit('click');f.button('광주').emit('click');assert.equal(f.changes(),0);
 f.elements.regionOpen.emit('click');f.dialog.emit('click',{target:f.dialog,clientX:0,clientY:0});assert.equal(f.dialog.open,false);assert.equal(f.changes(),0);
});
test('nationwide selection and browser back update the compact label and current selection',()=>{
 const f=fixture();f.elements.regionOpen.emit('click');f.button('all').emit('click');assert.equal(f.input.value,'all');assert.equal(f.elements.regionLabel.textContent,'전국');
 f.input.value='서울';f.windowEvents.popstate();assert.equal(f.elements.regionLabel.textContent,'서울');assert.equal(f.button('서울').attributes['aria-pressed'],'true');assert.equal(f.button('all').attributes['aria-pressed'],'false');
});
test('keyboard Tab and Shift-Tab wrap between the dialog last and first controls',()=>{
 const f=fixture();let prevented=0;
 f.dialog.emit('keydown',{key:'Tab',target:f.button('제주'),preventDefault(){prevented++;}});
 assert.equal(f.elements.regionClose.focused,true);
 f.dialog.emit('keydown',{key:'Tab',shiftKey:true,target:f.elements.regionClose,preventDefault(){prevented++;}});
 assert.equal(f.button('제주').focused,true);assert.equal(prevented,2);assert.equal(f.changes(),0);
});

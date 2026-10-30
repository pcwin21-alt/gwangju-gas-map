const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('Korean IME composition does not schedule search fits and direct map input cancels pending movement',()=>{
 const html=fs.readFileSync('output/map.html','utf8'),listeners={},input={value:'',addEventListener:(type,fn)=>listeners['input:'+type]=fn,focus(){}},clear={classList:{toggle(){},remove(){}},addEventListener:(type,fn)=>listeners['clear:'+type]=fn};
 let scheduled,filtered=0,fitted=0,cancelled=0;
 const context={document:{getElementById:id=>id==='searchInput'?input:clear,querySelector:()=>({addEventListener:(type,fn)=>listeners['map:'+type]=fn})},mapViewport:{fit(){fitted++;},cancelFit(){cancelled++;}},closeStationOverlay(){},window:{},map:{},kakao:{maps:{event:{addListener(){}}}},applyFilters(){filtered++;},setTimeout:fn=>(scheduled=fn,1),clearTimeout:()=>scheduled=null};
 vm.createContext(context);vm.runInContext(html.slice(html.indexOf('const searchInput ='),html.indexOf('// 자치구 필터')),context);
 input.value='돌고개';listeners['input:input']({isComposing:true});assert.equal(filtered,0);assert.equal(scheduled,undefined);
 listeners['input:compositionend']({});assert.equal(filtered,1);assert.equal(typeof scheduled,'function');
 listeners['map:touchstart']({target:{closest:()=>null}});assert.equal(scheduled,null);assert.equal(cancelled,1);assert.equal(fitted,0);
});

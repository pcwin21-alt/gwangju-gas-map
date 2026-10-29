const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function fixture() {
  const html=fs.readFileSync('output/map.html','utf8');
  const source=html.slice(html.indexOf('function locateUser('),html.indexOf("document.getElementById('myLocBtn').addEventListener"));
  const attributes={}, classes=new Set();
  const button={disabled:false,innerHTML:'<svg>location icon</svg>',setAttribute:(k,v)=>attributes[k]=v,classList:{add:c=>classes.add(c),remove:c=>classes.delete(c)}};
  let success, failure, centered;
  const context={navigator:{geolocation:{getCurrentPosition:(ok,fail)=>{success=ok;failure=fail;}}},alert(){},setCurrentLocation:(lat,lng,center)=>{centered=center;return {lat,lng};}};
  vm.createContext(context);vm.runInContext(source,context);
  return {button,attributes,classes,locate:()=>context.locateUser({button}),ok:()=>success({coords:{latitude:35.16,longitude:126.85}}),fail:()=>failure(new Error('denied')),centered:()=>centered};
}
test('location lookup retains icon, prevents duplicate button actions and restores success state',async()=>{
  const f=fixture(), pending=f.locate();
  assert.equal(f.button.disabled,true);assert.equal(f.attributes['aria-busy'],'true');
  f.ok();await pending;
  assert.equal(f.centered(),true);assert.equal(f.button.disabled,false);
  assert.equal(f.attributes['aria-busy'],'false');assert.ok(f.classes.has('located'));
  assert.equal(f.button.innerHTML,'<svg>location icon</svg>');
});
test('location failure leaves the icon and button available for retry',async()=>{
  const f=fixture(), pending=f.locate();f.fail();await assert.rejects(pending,/denied/);
  assert.equal(f.button.disabled,false);assert.equal(f.attributes['aria-busy'],'false');
  assert.equal(f.classes.has('loading'),false);assert.equal(f.button.innerHTML,'<svg>location icon</svg>');
});

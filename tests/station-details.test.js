const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('explicit station close removes the overlay and restores an accessible map control',()=>{
 const html=fs.readFileSync('output/map.html','utf8'),nodes=[];let removed=0,focused=0;
 const node=()=>{const n={children:[],attributes:{},dataset:{},listeners:{},classList:{add(){},remove(){}},append(...children){this.children.push(...children);},appendChild(child){this.append(child);},setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.listeners[k]=v;}};nodes.push(n);return n;};
 const context={document:{createElement:node,getElementById:id=>{assert.equal(id,'fitResultsBtn');return {focus(){focused++;}};}},activeOverlay:{setMap(value){assert.equal(value,null);removed++;}},PRICES:{},GasMerchantDisplay:{verificationText:()=>''},updateDistanceElement(){},getKakaoRouteUrl:()=>'',getNaverMapWebUrl:()=>'',window:{}};
 vm.createContext(context);vm.runInContext(html.slice(html.indexOf('function closeStationOverlay('),html.indexOf('function showStationOverlay(')),context);
 vm.runInContext(html.slice(html.indexOf('function buildInfoHtml('),html.indexOf('// 마커 생성')),context);
 context.buildInfoHtml({name:'테스트 주유소',address:'테스트 주소',lat:35,lng:126,payment_types:[]});
 const close=nodes.find(n=>n.attributes['aria-label']==='주유소 상세 닫기');assert.ok(close);close.listeners.click();
 assert.equal(context.activeOverlay,null);assert.equal(removed,1);assert.equal(focused,1);
 assert.ok(nodes.some(n=>n.attributes['aria-label']==='복사: 테스트 주소'));
});

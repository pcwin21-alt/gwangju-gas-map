const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('explicit station close removes the overlay and restores an accessible map control',()=>{
 const html=fs.readFileSync('output/map.html','utf8'),nodes=[];let removed=0,focused=0;
 const node=()=>{const n={children:[],attributes:{},dataset:{},listeners:{},classList:{add(){},remove(){}},append(...children){this.children.push(...children);},appendChild(child){this.append(child);},setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.listeners[k]=v;}};nodes.push(n);return n;};
 const context={document:{createElement:node,getElementById:id=>{assert.equal(id,'fitResultsBtn');return {focus(){focused++;}};}},activeOverlay:{setMap(value){assert.equal(value,null);removed++;}},PRICES:{},GasMerchantDisplay:require('../assets/merchant-display.js'),updateDistanceElement(){},getKakaoRouteUrl:()=>'/kakao',getNaverMapWebUrl:()=>'/naver',window:{}};
 vm.createContext(context);vm.runInContext(html.slice(html.indexOf('function closeStationOverlay('),html.indexOf('function showStationOverlay(')),context);
 vm.runInContext(html.slice(html.indexOf('function buildInfoHtml('),html.indexOf('// 마커 생성')),context);
 context.buildInfoHtml({name:'테스트 주유소',address:'테스트 주소',lat:35,lng:126,payment_types:[]});
 const close=nodes.find(n=>n.attributes['aria-label']==='주유소 상세 닫기');assert.ok(close);close.listeners.click();
 assert.equal(context.activeOverlay,null);assert.equal(removed,1);assert.equal(focused,1);
 assert.equal(nodes.some(n=>n.attributes['aria-label']?.startsWith('복사:')),false);
 assert.ok(nodes.some(n=>n.href==='/kakao'&&n.target==='_blank'));
 assert.ok(nodes.some(n=>n.href==='/naver'&&n.target==='_blank'));
 assert.equal(nodes.some(n=>n.className==='station-directions'),false);
 assert.equal(nodes.some(n=>n.className==='route-btn station-via'),false);
});

test('distance is absent until known, and updates without requesting location or resetting the map',()=>{
 const html=fs.readFileSync('output/map.html','utf8'),row={hidden:false},el={dataset:{lat:'35',lng:'126'},closest:()=>row,classList:{add(){},remove(){}}};
 const context={currentLocation:null,distanceKm:()=>1.25,formatDistance:km=>km+'km'};
 vm.createContext(context);vm.runInContext(html.slice(html.indexOf('function updateDistanceElement('),html.indexOf('function updateDistanceDisplays(')),context);
 context.updateDistanceElement(el);assert.equal(row.hidden,true);assert.equal(el.textContent,'');
 context.currentLocation={lat:35.1,lng:126};context.updateDistanceElement(el);assert.equal(row.hidden,false);assert.equal(el.textContent,'1.25km');
 el.dataset.lat='invalid';context.updateDistanceElement(el);assert.equal(row.hidden,true);assert.equal(el.textContent,'');
});

test('details show only valid fuel prices and only supported stations can be chosen as a stop',()=>{
 const html=fs.readFileSync('output/map.html','utf8'),nodes=[],chosen=[];
 const node=()=>{const n={children:[],dataset:{},listeners:{},append(...children){this.children.push(...children);},appendChild(child){this.append(child);},setAttribute(){},addEventListener(k,v){this.listeners[k]=v;}};nodes.push(n);return n;};
 const context={document:{createElement:node},PRICES:{a:{'휘발유':1800,'경유':0,LPG:900}},PRICE_INFO:{a:{source_dates:['20261030']}},GasPriceDisplay:require('../assets/price-display.js'),GasMerchantDisplay:require('../assets/merchant-display.js'),updateDistanceElement(){},getKakaoRouteUrl:()=>'/kakao',getNaverMapWebUrl:()=>'/naver',closeStationOverlay(){},window:{GasRoutePlanner:{chooseStation:s=>chosen.push(s.id)}}};
 vm.createContext(context);vm.runInContext(html.slice(html.indexOf('function buildInfoHtml('),html.indexOf('// 마커 생성')),context);
 context.buildInfoHtml({id:'a',name:'충전소',fuel_kind:'lpg',payment_types:['onnuri'],route_eligible:true});
 const price=nodes.find(n=>n.innerHTML?.includes('price-item')).innerHTML;
 assert.match(price,/LPG/);assert.match(price,/900원\/L/);assert.doesNotMatch(price,/휘발유|경유|1,800/);
 nodes.find(n=>n.className==='route-btn station-via').listeners.click();assert.deepEqual(chosen,['a']);
 nodes.length=0;context.PRICES.a={'휘발유':-10,'경유':NaN};
 context.buildInfoHtml({id:'a',name:'주유소',fuel_kind:'liquid',payment_types:[]});
 assert.equal(nodes.some(n=>n.innerHTML?.includes('price-item')),false);
 assert.equal(nodes.some(n=>n.innerHTML?.includes('가격 미확인')),false);
});
test('details stay in the viewport and an old station cannot clear a newer station card',()=>{
 const html=fs.readFileSync('output/map.html','utf8');
 const source=html.match(/const content=buildInfoHtml\(station\);\s*const overlay=\{setMap\(target\)\{[\s\S]*?\}\};/)[0];
 const host={hidden:true,firstElementChild:null,replaceChildren(node){this.firstElementChild=node||null;}};
 const make=id=>vm.runInNewContext(source+';overlay;',{station:{id},buildInfoHtml:s=>s,document:{getElementById:()=>host}});
 const a=make('a'),b=make('b');a.setMap({});assert.equal(host.firstElementChild.id,'a');assert.equal(host.hidden,false);
 b.setMap({});a.setMap(null);assert.equal(host.firstElementChild.id,'b');assert.equal(host.hidden,false);
 b.setMap(null);assert.equal(host.firstElementChild,null);assert.equal(host.hidden,true);
});

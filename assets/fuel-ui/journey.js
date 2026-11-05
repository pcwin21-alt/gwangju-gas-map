/* A selected station -> explicit origin -> route -> optional navigation. No polling. */
(() => {
  'use strict';
  const core=window.GasFuelJourneyCore,by=id=>document.getElementById(id),panel=by('fuelJourney');
  if(!core||!panel||!window.kakao?.maps)return;
  const config=window.GasJourneyConfig||{},local=['localhost','127.0.0.1'].includes(location.hostname),routeAvailable=Boolean(config.endpoint);
  panel.dataset.routeAvailable=String(routeAvailable);
  let station,origin,destination,overlays=[],routeBounds,view,controller,generation=0,searchVersion=0,historyOpen=false,picking=false,routeIsFixture=false;
  const say=text=>by('journeyStatus').textContent=text||'';
  function stop(){generation++;controller?.abort();controller=null;by('journeyCalculate').disabled=false;}
  function routeMode(active){document.querySelector('.map-area').classList.toggle('fuel-route-active',active);dispatchEvent(new Event('fuelroutevisibility'));}
  function clearRoute(){for(const item of overlays)item.setMap(null);overlays=[];routeBounds=null;routeIsFixture=false;routeMode(false);by('journeyEstimate').hidden=by('journeyRouteDate').hidden=by('journeyMap').hidden=true;}
  function fitRoute(){
    if(!routeBounds)return;
    mapViewport?.cancelFit?.();map.relayout();
    const mobile=matchMedia('(max-width:700px)').matches;
    map.setBounds(routeBounds,48,!mobile&&!panel.hidden?460:48,mobile&&!panel.hidden?Math.min(320,by('map').clientHeight*.5):72,48);
  }
  addEventListener('resize',()=>{if(routeBounds)requestAnimationFrame(fitRoute);});
  function restoreView(){
    if(!view)return;const saved={...view};
    const apply=()=>{mapViewport?.cancelFit?.();map.setLevel(saved.level);map.setCenter(new kakao.maps.LatLng(saved.lat,saved.lng));};
    apply();requestAnimationFrame(()=>requestAnimationFrame(apply));
  }
  function close({restore=true}={}){
    stop();searchVersion++;picking=false;clearRoute();panel.hidden=true;by('journeyRestore').hidden=true;
    if(!by('stationDetails').firstElementChild&&station){const item=allMarkers.find(i=>i.station.id===station.id);if(item)showStationOverlay(item.overlay);}
    by('stationDetails').hidden=!by('stationDetails').firstElementChild;if(restore)restoreView();view=null;
    by('stationDetails').querySelector('.fuel-journey-open')?.focus({preventScroll:true});
  }
  function exit(){if(historyOpen){history.back();}else close();}
  addEventListener('popstate',()=>{if(historyOpen){historyOpen=false;close();}});
  function selectOrigin(point){
    if(!core.point(point))return;
    stop();clearRoute();origin=point;by('journeyOrigin').textContent=point.name||'선택한 출발지';by('journeyChoices').replaceChildren();say('');
  }
  async function copyAddress(selected=station){
    if(!selected)return;
    const text=selected.name+'\n'+selected.address;
    try{
      if(window.GasJourneyBridge?.copy)await window.GasJourneyBridge.copy(text);
      else await navigator.clipboard.writeText(text);
      if(!panel.hidden)say('주유소 이름과 주소를 복사했어요.');else{const output=by('stationDetails').querySelector('.journey-copy-status');if(output)output.textContent='이름과 주소를 복사했어요.';}
    }catch(_){
      if(!panel.hidden){say('복사하지 못했어요. 아래 주소를 길게 눌러 복사해 주세요.');by('journeyAddress').style.userSelect='text';}
      else by('stationDetails').querySelector('.journey-copy-status').textContent='복사하지 못했어요. 표시된 주소를 직접 복사해 주세요.';
    }
  }
  function open(selected){
    stop();clearRoute();station=selected;
    if(!view){const c=map.getCenter();view={lat:c.getLat(),lng:c.getLng(),level:map.getLevel()};}
    by('journeyStation').textContent=station.name;by('journeyAddress').textContent=station.address;
    if(typeof currentLocation!=='undefined'&&core.point(currentLocation))origin={...currentLocation,name:'내 위치'};
    by('journeyOrigin').textContent=origin?.name||'출발지를 선택해 주세요';
    by('journeyTitle').textContent=routeAvailable?'주유소까지 경로':'지도앱으로 길찾기';
    panel.setAttribute('aria-label',by('journeyTitle').textContent);
    by('journeyApps').hidden=routeAvailable;by('journeyRestore').hidden=true;by('stationDetails').hidden=true;by('nationalResults').open=false;
    panel.hidden=false;say('');
    if(!historyOpen){history.pushState({...history.state,fuelJourney:true},'',location.href);historyOpen=true;}
    by('journeyClose').focus({preventScroll:true});
  }
  new MutationObserver(()=>{
    const host=by('stationDetails');if(!host.firstElementChild||host.querySelector('.fuel-journey-actions'))return;
    const selected=allMarkers.find(i=>i.overlay===activeOverlay)?.station;if(!selected)return;
    const actions=document.createElement('div');actions.className='fuel-journey-actions';
    const route=document.createElement('button');route.type='button';route.className='fuel-journey-open';route.textContent='경로 보기';
    route.textContent=routeAvailable?'경로 보기':'길찾기';
    route.disabled=selected.route_eligible!==true;route.addEventListener('click',()=>open(selected));
    const copy=document.createElement('button');copy.type='button';copy.textContent='주소 복사';copy.addEventListener('click',()=>copyAddress(selected));
    actions.append(route,copy);host.firstElementChild.append(actions);
    const feedback=document.createElement('p');feedback.className='journey-copy-status journey-meta';feedback.setAttribute('role','status');host.firstElementChild.append(feedback);
  }).observe(by('stationDetails'),{childList:true,subtree:true});
  by('journeyClose').addEventListener('click',exit);
  panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();exit();}});
  by('journeyCopy').addEventListener('click',()=>copyAddress());
  by('journeyRestore').addEventListener('click',()=>{picking=false;panel.hidden=false;by('journeyRestore').hidden=true;by('journeyClose').focus({preventScroll:true});});
  by('journeyPick').addEventListener('click',()=>{picking=true;panel.hidden=true;by('journeyRestore').hidden=false;by('journeyRestore').textContent='지도의 출발 지점을 누르세요';});
  kakao.maps.event.addListener(map,'click',event=>{
    if(!picking)return;picking=false;selectOrigin({lat:event.latLng.getLat(),lng:event.latLng.getLng(),name:'지도에서 선택한 출발지'});
    panel.hidden=false;by('journeyRestore').hidden=true;by('journeyRestore').textContent='경로 다시 보기';
  });
  by('journeyLocate').addEventListener('click',async()=>{
    const token=++searchVersion;by('journeyLocate').disabled=true;say('현재 위치를 확인하고 있어요.');
    try{
      const result=await new Promise((resolve,reject)=>{
        const api=window.GasToss||navigator.geolocation;
        if(!api)return reject(new Error());api.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:10000,maximumAge:60000});
      });
      if(token!==searchVersion||panel.hidden)return;
      selectOrigin({lat:result.coords.latitude,lng:result.coords.longitude,name:'내 위치'});
    }catch(_){if(token===searchVersion)say('위치를 확인하지 못했어요. 출발지를 검색하거나 지도에서 선택해 주세요.');}
    finally{by('journeyLocate').disabled=false;}
  });
  by('journeySearch').addEventListener('submit',event=>{
    event.preventDefault();const query=by('journeyQuery').value.trim(),version=++searchVersion;if(!query)return say('출발지 주소나 장소명을 입력해 주세요.');
    by('journeyQuery').blur();by('journeyChoices').replaceChildren();say('장소를 찾고 있어요.');
    new kakao.maps.services.Places().keywordSearch(query,(rows,status)=>{
      if(version!==searchVersion||panel.hidden)return;
      if(status!==kakao.maps.services.Status.OK)return say('장소를 찾지 못했어요. 주소를 바꾸거나 지도에서 선택해 주세요.');
      say('출발지를 선택해 주세요.');
      for(const row of rows.slice(0,5)){
        const button=document.createElement('button');button.type='button';button.textContent=row.place_name;
        const address=document.createElement('small');address.textContent=row.road_address_name||row.address_name;button.append(address);
        button.addEventListener('click',()=>selectOrigin({lat:Number(row.y),lng:Number(row.x),name:row.place_name}));by('journeyChoices').append(button);
      }
    },{size:5});
  });
  by('journeyQuery').addEventListener('input',()=>{stop();searchVersion++;origin=null;clearRoute();by('journeyOrigin').textContent='출발지를 선택해 주세요';by('journeyChoices').replaceChildren();});
  by('journeyDestinationQuery').addEventListener('input',()=>{stop();searchVersion++;destination=null;clearRoute();by('journeyDestinationLabel').textContent='';by('journeyDestinationChoices').replaceChildren();});
  by('journeyDestinationSearch').addEventListener('submit',event=>{
    event.preventDefault();const query=by('journeyDestinationQuery').value.trim(),version=++searchVersion;if(!query)return say('최종 목적지를 입력해 주세요.');
    by('journeyDestinationQuery').blur();by('journeyDestinationChoices').replaceChildren();say('목적지를 찾고 있어요.');
    new kakao.maps.services.Places().keywordSearch(query,(rows,status)=>{
      if(version!==searchVersion||panel.hidden)return;
      if(status!==kakao.maps.services.Status.OK)return say('목적지를 찾지 못했어요. 주소를 바꿔 주세요.');
      say('최종 목적지를 선택해 주세요.');
      for(const row of rows.slice(0,5)){
        const button=document.createElement('button');button.type='button';button.textContent=row.place_name;
        const address=document.createElement('small');address.textContent=row.road_address_name||row.address_name;button.append(address);
        button.addEventListener('click',()=>{stop();clearRoute();destination={lat:Number(row.y),lng:Number(row.x),name:row.place_name};by('journeyDestinationLabel').textContent='최종 목적지 · '+destination.name;by('journeyDestinationChoices').replaceChildren();say('');});by('journeyDestinationChoices').append(button);
      }
    },{size:5});
  });
  by('journeyDestinationClear').addEventListener('click',()=>{stop();clearRoute();destination=null;by('journeyDestinationQuery').value='';by('journeyDestinationLabel').textContent='';by('journeyDestinationChoices').replaceChildren();say('주유소까지의 경로를 확인할 수 있어요.');});
  by('journeyCalculate').addEventListener('click',async()=>{
    if(!origin)return say('출발지를 먼저 선택해 주세요.');
    stop();clearRoute();const token=generation;controller=new AbortController();const active=controller;
    by('journeyCalculate').disabled=true;say('자동차 경로를 확인하고 있어요.');const timer=setTimeout(()=>active.abort(),12000);
    try{
      if(!config.endpoint)throw new Error('자동차 경로 연결을 준비 중이에요. 주소를 복사하거나 지도앱에서 위치를 확인해 주세요.');
      const fetchRoute=async payload=>{
        const response=await fetch(config.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:active.signal});
        const body=await response.json();if(!response.ok)throw new Error(body.message||'경로를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.');return core.route(body);
      };
      const data=await fetchRoute(core.request(origin,station,destination));
      let extra=null;
      if(destination){
        try{const base=await fetchRoute(core.request(origin,{...destination,route_eligible:true}));extra=core.addedSeconds(base,data);}catch(_){extra=null;}
      }
      if(token!==generation)return;
      routeIsFixture=Boolean(data.fixture);
      by('journeyTitle').textContent=destination?'주유소 경유 경로':'주유소까지 경로';
      panel.setAttribute('aria-label',by('journeyTitle').textContent);
      by('journeyEstimate').textContent=`${destination?'전체 ':''}약 ${Math.max(1,Math.ceil(data.seconds/60))}분 · ${(data.meters/1000).toFixed(1)}km`;
      by('journeyRouteDate').textContent=(data.fixture?'검수용 모의 응답 · 실제 운전에 사용하지 마세요.':data.provider+' · '+new Date(data.checkedAt).toLocaleTimeString('ko-KR')+' 조회')+' · 주유·대기 시간 제외';
      by('journeyEstimate').hidden=by('journeyRouteDate').hidden=by('journeyMap').hidden=false;
      const path=data.coordinates.map(c=>new kakao.maps.LatLng(c[1],c[0]));
      overlays.push(new kakao.maps.Polyline({map,path,strokeWeight:9,strokeColor:'#fff',strokeOpacity:1,zIndex:90}),new kakao.maps.Polyline({map,path,strokeWeight:5,strokeColor:'#285BB5',strokeOpacity:1,zIndex:91}));
      for(const [point,label] of [[origin,'출발'],[station,'주유소'],...(destination?[[destination,'목적지']]:[])]){
        const content=document.createElement('span');content.className='journey-map-label';content.textContent=label;
        overlays.push(new kakao.maps.CustomOverlay({map,position:new kakao.maps.LatLng(point.lat,point.lng),content,yAnchor:1.3,zIndex:200}));
      }
      routeBounds=new kakao.maps.LatLngBounds();path.forEach(p=>routeBounds.extend(p));routeMode(true);fitRoute();
      say(destination?origin.name+' → '+station.name+' → '+destination.name+' · '+(extra===null?'추가 이동시간 미확인':'추가 약 '+Math.ceil(extra/60)+'분'):'경로를 확인했어요.');
    }catch(error){if(token===generation)say(error.name==='AbortError'?'경로 조회 시간이 초과됐어요. 다시 확인하거나 주소를 복사해 주세요.':error instanceof TypeError||error instanceof SyntaxError?'경로 서버에 연결하지 못했어요. 다시 확인하거나 주소를 복사해 주세요.':error.message);}
    finally{clearTimeout(timer);if(token===generation)by('journeyCalculate').disabled=false;}
  });
  by('journeyMap').addEventListener('click',()=>{panel.hidden=true;by('journeyRestore').hidden=false;by('journeyRestore').textContent=routeIsFixture?'모의 경로 · 다시 보기':'경로 다시 보기';requestAnimationFrame(fitRoute);});
  by('journeyNavigate').addEventListener('click',()=>{by('journeyApps').hidden=!by('journeyApps').hidden;if(destination)say('지도앱은 주유소까지만 안내해요. 최종 목적지: '+destination.name);});
  for(const button of panel.querySelectorAll('[data-journey-app]'))button.addEventListener('click',async()=>{
    if(!local&&!config.externalNavigationEnabled)return say('이 환경에서는 지도앱 연결을 사용할 수 없어요. 주소를 복사해 주세요.');
    const app=button.dataset.journeyApp;
    const url=app==='naver'&&!window.GasJourneyBridge?.openURL?getNaverMapWebUrl(station):core.links(station,location.origin)[app];button.disabled=true;
    try{
      if(window.GasJourneyBridge?.openURL)await window.GasJourneyBridge.openURL(url);
      else if(config.externalNavigationEnabled||local){const opened=window.open(url,'_blank','noopener');void opened;}
      else throw new Error();
      say('지도앱 연결을 요청했어요. 열리지 않으면 다른 지도앱을 선택하거나 주소를 복사해 주세요.');
    }catch(_){say('지도앱을 열지 못했어요. 다른 지도앱을 선택하거나 주소를 복사해 주세요.');}
    finally{button.disabled=false;}
  });
  function dismissForChange(){if(historyOpen){historyOpen=false;const state={...history.state};delete state.fuelJourney;history.replaceState(state,'',location.href);close({restore:false});}}
  for(const id of ['filtersToggle','regionOpen','toolsOpenBtn','resetBtn'])by(id).addEventListener('click',dismissForChange,{capture:true});
  by('searchInput').addEventListener('focus',dismissForChange,{capture:true});
  by('resetBtn').addEventListener('click',()=>{origin=null;destination=null;});
})();

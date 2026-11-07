/* Local design review only. No new request, telemetry or data source. */
(() => {
  if(new URL(location.href).searchParams.get('text')==='large'){
    document.documentElement.style.fontSize='200%';document.documentElement.dataset.reviewText='large';
  }
  const panel=document.getElementById('mapFilters'),toggle=document.getElementById('filtersToggle');
  const extraFilters=document.createElement('p');extraFilters.id='reviewExtraFilters';extraFilters.hidden=true;document.querySelector('.controls').append(extraFilters);
  const setClosed=()=>{panel.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus({preventScroll:true});};
  const close=document.createElement('button');close.type='button';close.textContent='닫기';close.setAttribute('aria-label','검색 필터 닫기');close.addEventListener('click',setClosed);
  const reset=document.getElementById('filtersReset'),foot=document.createElement('div');foot.className='review-filter-foot';
  const done=document.createElement('button');done.id='reviewFiltersDone';done.type='button';done.textContent='지도 보기';done.addEventListener('click',setClosed);
  panel.querySelector('.filters-heading').append(close);foot.append(reset,done);panel.append(foot);
  panel.addEventListener('cancel',event=>{event.preventDefault();setClosed();});
  panel.addEventListener('close',()=>{if(!panel.hidden)setClosed();});
  new MutationObserver(()=>{if(panel.hidden){if(panel.open)panel.close();}else if(!panel.open)panel.showModal();}).observe(panel,{attributes:true,attributeFilter:['hidden']});
  const syncLabel=()=>{
    const labels=document.getElementById('activeFilters').textContent.trim();
    const payment=document.querySelector('.filter-btn.active')?.dataset.filter;
    const label=toggle.querySelector('span');label.textContent=payment==='onnuri'?'온누리':['local','saengsaeng'].includes(payment)?'지역화폐':'필터';
    const rest=labels.split(' · ').filter(value=>value&&value!==label.textContent);extraFilters.textContent=rest.join(' · ');extraFilters.hidden=!rest.length;
    toggle.dataset.reviewSelected=String(Boolean(labels));
    toggle.setAttribute('aria-label',labels?'필터, '+labels:'필터');
  };
  new MutationObserver(syncLabel).observe(document.getElementById('activeFilters'),{childList:true,characterData:true,subtree:true});syncLabel();
  document.getElementById('searchInput').placeholder='주유소명 · 주소 검색';
  const detailHost=document.getElementById('stationDetails');
  const splitUnits=()=>detailHost.querySelectorAll('.price-item b').forEach(value=>{
    if(value.querySelector('.review-price-number'))return;
    const match=value.textContent.match(/^([\d,]+)(원\/L)$/);if(!match)return;
    const number=document.createElement('span');number.className='review-price-number';number.textContent=match[1];
    const unit=document.createElement('small');unit.textContent=match[2];value.replaceChildren(number,unit);
  });
  new MutationObserver(splitUnits).observe(detailHost,{childList:true,subtree:true});
  const formatResultDates=()=>document.querySelectorAll('.station-list-row .station-price').forEach(value=>{
    if(value.querySelector('.review-price-date'))return;
    const match=value.textContent.match(/^(.*) · 유가 (.+)$/);if(!match)return;
    const date=document.createElement('small');date.className='review-price-date';date.textContent='유가 '+match[2]+' 기준';value.replaceChildren(document.createTextNode(match[1]),date);
  });
  new MutationObserver(formatResultDates).observe(document.getElementById('stationList'),{childList:true,subtree:true});
  document.querySelector('.rank-panel-title').textContent='가격 낮은 순 · 현재 조건';
  document.querySelector('.help-panel-title').textContent='사용 안내';
  document.querySelectorAll('.help-dot').forEach((dot,index)=>{dot.style.backgroundColor=['#3e50a0','#1d3b31','#6851a2'][index];});
  document.querySelectorAll('.help-section').forEach(section=>{
    const title=section.querySelector('.help-section-title');
    if(title?.textContent.trim()==='공유 안내'){title.textContent='문의';section.querySelector('.help-item')?.remove();}
  });
  const formatRank=()=>document.querySelectorAll('#rankList .rank-item').forEach((row,index)=>{
    row.querySelector('.rank-badge').textContent=String(index+1);
    if(row.querySelector('.review-price-date'))return;
    const dates=typeof PRICE_INFO!=='undefined'?PRICE_INFO[row.dataset.id]?.source_dates:[];
    if(!dates?.length)return;
    const note=document.createElement('div');note.className='review-price-date';
    note.textContent='유가 '+dates.map(d=>/^\d{8}$/.test(d)?d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6):d).join(' · ')+' 기준';row.querySelector('.rank-info').append(note);
  });
  new MutationObserver(formatRank).observe(document.getElementById('rankList'),{childList:true});
  const openReviewState=()=>{
    const view=new URL(location.href).searchParams.get('view');
    if(view==='filters')toggle.click();
    if(view==='region')document.getElementById('regionOpen').click();
    if(view==='more')document.getElementById('toolsOpenBtn').click();
    if(view==='policy')document.getElementById('policyOpen').click();
    if(view==='detail'&&typeof allMarkers!=='undefined'&&window.kakao?.maps){
      const item=allMarkers.find(row=>row.station.name==='서양새마을금고 주유소');
      if(item){map.setCenter(new kakao.maps.LatLng(item.station.lat,item.station.lng));map.setLevel(4);showStationOverlay(item.overlay);}
    }
  };
  if(document.readyState==='complete')openReviewState();else window.addEventListener('load',openReviewState,{once:true});
})();

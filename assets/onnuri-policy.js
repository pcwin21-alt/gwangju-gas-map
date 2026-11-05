/* Public policy information only. No location, identity, purchase or merchant lookup. */
(() => {
  'use strict';
  const core=GasOnnuriPolicy,byId=id=>document.getElementById(id);
  const open=byId('policyOpen'),menu=byId('policyMenuOpen'),dialog=byId('policyDialog');
  if(!open||!dialog)return;
  const toss=document.documentElement.dataset.platform==='toss';
  dialog.dataset.policySource='cached';
  let data=GasOnnuriPolicyData,returnFocus=open,lastState='',clock;
  const stateKey=view=>JSON.stringify([view.today,view.fresh,view.rate,view.notices.map(n=>[n.id,n.state.kind])]);
  function scheduleClock(){clearTimeout(clock);const now=new Date();clock=setTimeout(refreshClock,Math.max(1,Math.min(60000,core.nextTransitionAt(data,now)-now.getTime())));}
  function refreshClock(){if(stateKey(core.snapshot(data))!==lastState)render();else scheduleClock();}
  const text=(tag,value,cls)=>{const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;};
  function link(label,url){const node=text('a',label);node.href=url;node.target='_blank';node.rel='noopener noreferrer';return node;}
  function render(){
    const view=core.snapshot(data);lastState=stateKey(view);
    byId('policyLabel').textContent=view.label;
    open.classList.toggle('has-special',Boolean(view.promotion));
    const limit=view.promotion?.purchaseLimitKRW?`${view.promotion.purchaseLimitKRW/10000}만원 구간 `:'';
    const special=view.promotion?` · ${limit}${view.promotion.rate}% 특별할인 공지 있음`:'';
    open.setAttribute('aria-label',view.label+special+' · 정책과 이용 안내 열기');
    open.title=view.label+special;byId('policySpecial').hidden=!view.promotion;
    const current=byId('policyCurrent');current.replaceChildren();
    current.append(text('span','디지털 온누리상품권','policy-eyebrow'),text('h3',view.fresh?`기본 구매할인 ${view.rate}%`:'현재 혜택을 다시 확인해 주세요'));
    if(view.promotion)current.append(text('p',`${view.promotion.startsOn.slice(5).replace('-','/')}~${view.promotion.endsOn.slice(5).replace('-','/')} ${limit}특별할인 ${view.promotion.rate}% 공지`,'policy-special'));
    current.append(text('p','상품권 구매·충전에 적용되는 할인입니다. 주유 가격·가맹 상태는 별도로 확인하세요.','policy-meta'));
    if(!view.fresh)current.append(text('p','아래 내용은 마지막 확인 자료입니다. 최신 공식 공지에서 실제 적용 조건을 확인하세요.','policy-warning'));
    byId('policyChecked').textContent=`공식 자료 확인 ${data.checkedAt}`;
    const list=byId('policyNews');
    const expanded=new Set([...list.querySelectorAll('[data-notice-id]')].filter(n=>n.querySelector('details')?.open).map(n=>n.dataset.noticeId));
    list.replaceChildren();
    for(const notice of view.notices){
      const article=text('article','','policy-news-item');article.dataset.state=notice.state.kind;article.dataset.noticeId=notice.id;
      article.append(text('span',notice.state.label,'policy-state'),text('h3',notice.title));
      const timing=notice.kind==='planned'?`추진연도 ${notice.plannedYear||'미확인'}`:
        `적용 기간 ${notice.startsOn}${notice.endsOn?' ~ '+notice.endsOn:''}`;
      article.append(text('p',`발표 ${notice.publishedAt} · ${timing}`,'policy-meta'),text('p',notice.summary));
      const details=document.createElement('details');details.open=expanded.has(notice.id);details.append(text('summary','조건과 공식 출처'));
      const ul=document.createElement('ul');for(const detail of notice.details)ul.append(text('li',detail));details.append(ul);
      const source=data.sources.find(s=>s.id===notice.sourceId);
      if(source.checkedAt)details.append(text('p',`해당 원문 확인 ${source.checkedAt}`,'policy-meta'));
      details.append(link(source.publisher+' · 원문 ↗',source.url));
      if(source.documentUrl)details.append(link('공식 첨부문서 ↗',source.documentUrl));
      article.append(details);list.append(article);
    }
    const signup=byId('policySignup');signup.replaceChildren(text('h3','처음 이용한다면'));
    const steps=document.createElement('ol');for(const step of data.registration.steps)steps.append(text('li',step));signup.append(steps);
    if(!toss){const links=text('div','','policy-signup-links');for(const item of data.registration.links)links.append(link(item.label+' ↗',item.url));signup.append(links);}
    signup.append(text('p','상품권 가입·충전·결제는 공식 서비스에서 진행하며, 이 지도는 독립 정보 서비스입니다.','policy-meta'));
    scheduleClock();
  }
  function show(event){returnFocus=event.currentTarget;render();dialog.showModal();}
  open.addEventListener('click',show);menu?.addEventListener('click',show);
  byId('policyClose').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{const target=returnFocus?.getClientRects().length?returnFocus:byId('toolsOpenBtn');target?.focus({preventScroll:true});});
  dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
  render();
  async function refresh(){
    const url=toss?'https://pcwin21-alt.github.io/gwangju-gas-map/assets/onnuri-policy.json':new URL('assets/onnuri-policy.json',document.baseURI).href;
    try{
      const response=await fetch(url,{credentials:'omit',referrerPolicy:'no-referrer',cache:'no-cache',signal:AbortSignal.timeout(6000)});
      if(!response.ok)throw new Error('Policy unavailable');
      const incoming=await response.json();
      if(!core.validate(incoming)||incoming.checkedAt<data.checkedAt||incoming.checkedAt>core.koreanDay())throw new Error('Unverified policy payload');
      data=incoming;render();dialog.dataset.policySource='published';byId('policyLiveState').hidden=true;
    }catch(_){dialog.dataset.policySource='cached';byId('policyLiveState').hidden=false;byId('policyLiveState').textContent='연결이 원활하지 않아 마지막 확인 자료를 표시해요.';}
  }
  byId('policyRefresh').addEventListener('click',()=>{const button=byId('policyRefresh');if(button.getAttribute('aria-busy')==='true')return;button.setAttribute('aria-busy','true');refresh().finally(()=>button.setAttribute('aria-busy','false'));});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshClock();});
  refresh();
})();

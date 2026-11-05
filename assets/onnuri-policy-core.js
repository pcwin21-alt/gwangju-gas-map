(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.GasOnnuriPolicy=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const dayPattern=/^\d{4}-\d{2}-\d{2}$/;
  const dateValid=value=>typeof value==='string'&&dayPattern.test(value)&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
  const allowedHosts=new Set(['www.korea.kr','m.korea.kr','www.mss.go.kr','www.semas.or.kr','www.komsco.com','www.onnuri.gift','play.google.com','apps.apple.com']);
  const stampValid=(value,day)=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\+09:00$/.test(value)&&value.slice(0,10)===day&&Number.isFinite(Date.parse(value));
  function safeURL(value){try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password&&allowedHosts.has(url.hostname);}catch(_){return false;}}
  function validate(data){
    try {
      if(data?.schemaVersion!==1||!dateValid(data.checkedAt)||!Number.isInteger(data.reviewAfterDays)||data.reviewAfterDays<1||data.reviewAfterDays>7)return false;
      if(!Number.isFinite(data.digitalBase?.rate)||data.digitalBase.rate<0||data.digitalBase.rate>30||!dateValid(data.digitalBase.recheckBy))return false;
      if(!Array.isArray(data.sources)||!data.sources.length||data.sources.length>30||!Array.isArray(data.notices)||data.notices.length>30)return false;
      const ids=new Set(data.sources.map(s=>s.id));
      if(ids.size!==data.sources.length||!ids.has(data.digitalBase.sourceId))return false;
      if(!data.sources.every(s=>safeURL(s.url)&&(!s.documentUrl||safeURL(s.documentUrl))&&typeof s.publisher==='string'&&typeof s.title==='string'))return false;
      if(!data.notices.every(n=>['temporary','planned','confirmed'].includes(n.kind)&&dateValid(n.publishedAt)&&ids.has(n.sourceId)&&typeof n.title==='string'&&typeof n.summary==='string'&&Array.isArray(n.details)&&n.details.every(t=>typeof t==='string')&&
        (n.kind==='planned'?!n.startsOn:dateValid(n.startsOn)&&(!n.endsOn||dateValid(n.endsOn)&&n.endsOn>=n.startsOn))&&(!n.affects||n.affects==='digital_base'&&n.kind==='confirmed'&&Number.isFinite(n.rate))&&(!('rate'in n)||Number.isFinite(n.rate)&&n.rate>=0&&n.rate<=30)))return false;
      if(!data.notices.every(n=>(!('startsAt'in n)||stampValid(n.startsAt,n.startsOn))&&(!('endsAt'in n)||stampValid(n.endsAt,n.endsOn))&&(!n.startsAt||!n.endsAt||n.startsAt<n.endsAt)&&(!('purchaseLimitKRW'in n)||Number.isInteger(n.purchaseLimitKRW)&&n.purchaseLimitKRW>0)))return false;
      return Array.isArray(data.registration?.steps)&&data.registration.steps.every(s=>typeof s==='string')&&Array.isArray(data.registration.links)&&data.registration.links.every(l=>safeURL(l.url)&&typeof l.label==='string');
    }catch(_){return false;}
  }
  function koreanDay(now=new Date()){
    const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
    const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));return `${p.year}-${p.month}-${p.day}`;
  }
  function noticeState(notice,today,now){
    if(notice.kind==='planned')return {label:'추진안 · 시행일 미정',kind:'planned'};
    if(now&&notice.startsAt&&now.getTime()<Date.parse(notice.startsAt))return {label:'시행 예정',kind:'upcoming'};
    if(now&&notice.endsAt&&now.getTime()>=Date.parse(notice.endsAt))return {label:'기간 종료',kind:'ended'};
    if(today<notice.startsOn)return {label:'시행 예정',kind:'upcoming'};
    if(notice.endsOn&&today>notice.endsOn)return {label:'기간 종료',kind:'ended'};
    return {label:notice.kind==='temporary'?'기간 한정 공지':'시행 중',kind:'active'};
  }
  function snapshot(data,now=new Date()){
    if(!validate(data))return {fresh:false,label:'온누리 혜택·정책',notices:[]};
    const today=koreanDay(now),age=(Date.parse(today)-Date.parse(data.checkedAt))/86400000;
    const fresh=age>=0&&age<=data.reviewAfterDays&&today<=data.digitalBase.recheckBy;
    const notices=data.notices.map(n=>({...n,state:noticeState(n,today,now)}));
    const baseChange=notices.filter(n=>n.kind==='confirmed'&&n.affects==='digital_base'&&n.state.kind==='active').sort((a,b)=>b.startsOn.localeCompare(a.startsOn))[0];
    const rate=baseChange?.rate??data.digitalBase.rate;
    const promotion=notices.find(n=>n.kind==='temporary'&&n.state.kind==='active');
    return {today,fresh,rate:fresh?rate:null,promotion:fresh?promotion:null,notices,
      label:fresh?`온누리 기본 ${rate}%`:'온누리 혜택·정책'};
  }
  function nextTransitionAt(data,now=new Date()){
    const at=now.getTime(),midnight=Date.parse(koreanDay(now)+'T00:00:00+09:00')+86400000;
    const dates=(data.notices||[]).flatMap(n=>n.kind==='planned'?[]:[n.startsAt,n.endsAt]).filter(Boolean).map(Date.parse).filter(t=>Number.isFinite(t)&&t>at);
    return Math.min(midnight,...dates);
  }
  return {validate,safeURL,koreanDay,noticeState,snapshot,nextTransitionAt};
});

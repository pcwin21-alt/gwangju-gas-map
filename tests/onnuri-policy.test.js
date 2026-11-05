const test=require('node:test'),assert=require('node:assert/strict');
const core=require('../assets/onnuri-policy-core.js'),data=require('./fixtures/onnuri-policy-20261104.json');

test('basic purchase discount and a temporary promotion retain different scopes',()=>{
 assert.equal(core.validate(require('../assets/onnuri-policy-data.js')),true);
 const current=core.snapshot(data,new Date('2026-11-04T10:00:00Z'));
 assert.equal(current.fresh,true);assert.equal(current.rate,7);assert.equal(current.promotion.rate,10);
 assert.match(current.label,/기본 7%/);assert.equal(current.notices.find(n=>n.id==='reform-2027').state.kind,'planned');
});
test('temporary notices end on the Korean calendar date, not the UTC date',()=>{
 const notice=data.notices.find(n=>n.id==='kgf-2026');
 assert.equal(core.noticeState(notice,core.koreanDay(new Date('2026-11-06T14:59:00Z'))).kind,'active');
 assert.equal(core.noticeState(notice,core.koreanDay(new Date('2026-11-06T15:00:00Z'))).kind,'ended');
 assert.equal(core.snapshot(data,new Date('2026-11-07T01:00:00Z')).promotion,undefined);
});
test('an unconfirmed 2027 plan never becomes a current discount merely because time passes',()=>{
 const notice=data.notices.find(n=>n.kind==='planned');
 assert.equal(core.noticeState(notice,'2027-01-01').kind,'planned');
 assert.equal(core.noticeState(notice,'2027-08-01').kind,'planned');
});
test('only an explicitly confirmed purchase-base change activates at its Korean start date',()=>{
 const hypothetical=structuredClone(data);
 hypothetical.notices.push({...hypothetical.notices[0],id:'test-confirmed-base',kind:'confirmed',affects:'digital_base',rate:5,startsOn:'2026-11-06',endsOn:null});
 assert.equal(core.snapshot(hypothetical,new Date('2026-11-05T14:59:00Z')).rate,7);
 assert.equal(core.snapshot(hypothetical,new Date('2026-11-05T15:00:00Z')).rate,5);
 hypothetical.notices.at(-1).kind='planned';hypothetical.notices.at(-1).startsOn=null;
 assert.equal(core.validate(hypothetical),false);
});
test('stale, future-dated, or year-boundary data cannot claim a current numeric discount',()=>{
 for(const date of ['2026-11-12T00:00:00Z','2026-11-03T00:00:00Z','2027-01-01T00:00:00Z']){
  const current=core.snapshot(data,new Date(date));assert.equal(current.fresh,false);assert.equal(current.rate,null);assert.doesNotMatch(current.label,/%/);
 }
});
test('unsafe URLs and malformed date/rate payloads cannot replace reviewed fallback data',()=>{
 assert.equal(core.validate(data),true);
 for(const mutate of [d=>d.sources[0].url='javascript:alert(1)',d=>d.sources[0].url='https://example.com/fake',d=>d.digitalBase.rate=99,d=>d.checkedAt='2026-02-30',d=>d.notices[1].startsOn='2027-01-01']){
  const changed=structuredClone(data);mutate(changed);assert.equal(core.validate(changed),false);
 }
});

test('the official special-sale window ends at 23:30 KST, before the calendar day ends',()=>{
 const live=require('../assets/onnuri-policy-data.js'),notice=live.notices.find(n=>n.id==='kgf-2026');
 for(const [at,expected] of [['2026-11-01T15:29:59Z','upcoming'],['2026-11-01T15:30:00Z','active'],['2026-11-06T14:29:59Z','active'],['2026-11-06T14:30:00Z','ended']]){
   const now=new Date(at);assert.equal(core.noticeState(notice,core.koreanDay(now),now).kind,expected);
 }
 assert.equal(core.snapshot(live,new Date('2026-11-06T14:30:00Z')).promotion,undefined);
 assert.equal(core.nextTransitionAt(live,new Date('2026-11-06T14:29:00Z')),Date.parse('2026-11-06T14:30:00Z'));
});

test('paper limits and special-sale limits do not replace the digital base discount or invent a plan date',()=>{
 const live=require('../assets/onnuri-policy-data.js'),view=core.snapshot(live,new Date('2026-11-05T01:00:00Z'));
 assert.equal(view.rate,7);assert.equal(view.promotion.purchaseLimitKRW,200000);
 assert.equal(view.notices.find(n=>n.id==='paper-monthly-limit-2026').state.kind,'active');
 assert.equal(view.notices.find(n=>n.id==='reform-2027').startsOn,null);
 assert.equal(live.checkedAt,'2026-11-04');assert.equal(live.sources.find(s=>s.id==='paper-limit-2026').checkedAt,'2026-11-05');
 assert.equal(core.safeURL('https://www.onnuri.gift/news/notice/detail?no=44'),true);
 assert.equal(core.safeURL('https://www.onnuri.gift.evil.test/news'),false);
});

test('a timestamp cannot disagree with its Korean date or use an unannounced timezone',()=>{
 for(const mutate of [n=>n.endsAt='2026-11-07T23:30:00+09:00',n=>n.endsAt='2026-11-06T14:30:00Z',n=>n.purchaseLimitKRW=-1]){
  const live=structuredClone(require('../assets/onnuri-policy-data.js'));mutate(live.notices[0]);assert.equal(core.validate(live),false);
 }
});


const test = require('node:test');
const assert = require('node:assert/strict');
const data = require('../assets/regional-benefits-data.js');
const currencies = require('../assets/regional-currency.js');

test('specific currency takes precedence, while explicit Onnuri always keeps its own button', () => {
  assert.equal(data.context('광주', 'onnuri', currencies), null);
  assert.equal(data.context('전국', 'incheon-eum', currencies), 'incheon-eum');
  assert.equal(data.context('울산', null, currencies), 'ulsan-pay');
  assert.equal(data.context('all', 'local', currencies), 'local');
  assert.equal(data.context('전남', null, currencies), null);
});

test('conditional campaigns retain their separate terms, and fall back at Korean date boundaries', () => {
  const view = data.snapshot('incheon-eum', '2026-11-08');
  assert.equal(view.current.label, '한시 캐시백 15%');
  assert.equal(view.base.label, '기본 캐시백 10%');
  assert.equal(view.notices[0].state, '기간 한정 공지');
  assert.equal(data.snapshot('incheon-eum', '2026-11-15').current.label, '한시 캐시백 15%');
  assert.equal(data.snapshot('incheon-eum', '2026-11-16').notices[0].state, '기간 종료');
  assert.equal(data.snapshot('incheon-eum', '2026-11-16').current, null);
});

test('early closures and unconfirmed rates do not become current offers', () => {
  assert.equal(data.snapshot('busan-dongbaek', '2026-11-08').current.label, '기본 캐시백 8~10%');
  const ulsan = data.snapshot('ulsan-pay', '2026-11-08');
  assert.equal(ulsan.current.label, '캐시백 13%');
  assert.equal(ulsan.notices[0].state, '종료');
  assert.equal(data.snapshot('yeominjeon', '2026-11-08').current, null);
  assert.equal(data.snapshot('saengsaeng', '2026-11-07').current, null);
});

test('every supported currency has an official HTTPS entry and dated evidence for any displayed rate', () => {
  const supported = currencies.available(Object.keys(data.policies).map(id => ({payment_types:[id]})));
  assert.equal(supported.length, 8);
  for (const id of supported) {
    const policy = data.policies[id];
    for (const url of [policy.official, policy.base?.source, ...(policy.notices || []).map(n => n.source)].filter(Boolean)) {
      const link = new URL(url);
      assert.equal(link.protocol, 'https:');
      assert.equal(link.username, '');
      assert.equal(link.password, '');
    }
    if (data.snapshot(id, '2026-11-08').current) assert.equal(policy.checkedOn, '2026-11-08');
  }
});

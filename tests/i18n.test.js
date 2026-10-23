const test = require('node:test');
const assert = require('node:assert/strict');
const {translate} = require('../assets/i18n.js');
test('UI text and fuel amounts translate without altering numbers', () => {
  assert.equal(translate('상생카드'), 'Sangsaeng');
  assert.equal(translate('  1,636.2원/L  '), '  KRW 1,636.2/L  ');
  assert.equal(translate('71곳'), '71 stations');
  assert.equal(translate('추가 이동 약 8분 · 3.5km'), 'Approx. detour: 8 min · 3.5km');
});
test('verification and route messages retain source dates and names', () => {
  assert.equal(translate('온누리 공식 검색 확인 2026-10-23'),'Onnuri Official search checked: 2026-10-23');
  assert.equal(translate('온누리 공식 자료 2026-07-31'), 'Onnuri Official source: 2026-07-31');
  assert.equal(translate('선택됨: 광주역'), 'Selected: 광주역');
  assert.equal(translate('상생카드 조회: 2026-10-13 / 온누리 공식 자료 2026-07-31'), 'Sangsaeng checked: 2026-10-13 / Onnuri Official source: 2026-07-31');
});
test('unknown station names, addresses and user input remain unchanged', () => {
  for (const text of ['돌고개주유소','광주광역시 서구 경열로 54','온누리주유소','내가 입력한 메모']) assert.equal(translate(text),text);
});

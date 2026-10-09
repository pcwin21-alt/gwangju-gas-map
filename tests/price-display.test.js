const test = require('node:test');
const assert = require('node:assert/strict');
const prices = require('../assets/price-display.js');
const sang = {payment_types: ['saengsaeng', 'onnuri']};
test('10 percent effective unit price preserves fractional won', () => {
  assert.equal(prices.effectivePrice(1818, sang), 1636.2);
  assert.equal(prices.effectivePrice(1819, sang), 1637.1);
  assert.match(prices.html(1818, sang), /<del[^>]*>1,818원\/L<\/del> <b>1,636.2원\/L<\/b>/);
});
test('discount is restricted to Sangsaeng merchants with valid prices', () => {
  for (const station of [undefined, {}, {payment_types: ['onnuri']}]) {
    assert.equal(prices.effectivePrice(1818, station), 1818);
    assert.doesNotMatch(prices.html(1818, station), /<del|10%/);
  }
  for (const price of [null, '1818', NaN, Infinity, 0, -1]) assert.equal(prices.html(price, sang), '');
});

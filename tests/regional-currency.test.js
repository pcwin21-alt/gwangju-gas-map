const { test } = require('node:test');
const assert = require('node:assert/strict');
const regional = require('../assets/regional-currency.js');
const merchant = require('../assets/merchant-display.js');
const route = require('../assets/route-core.js');

const station = { id: 'station', region: '인천', name: '테스트 주유소', address: '인천 테스트로 1',
  lat: 37.45, lng: 126.70, fuel_kind: 'liquid', payment_types: ['onnuri'],
  verification: { onnuri: { status: 'confirmed', checked_at: '2026-11-07' } } };
const verification = { status: 'confirmed', checked_at: '2026-11-08', channels: ['card'],
  source_url: 'https://incheoneum.or.kr/store/payment/' };
const entry = { stationId: station.id, currency: 'incheon-eum', verification };

test('a regional card attaches to one existing pin without replacing Onnuri evidence', () => {
  const [result, ...rest] = regional.mergeStations([station], [entry, entry]);
  assert.equal(rest.length, 0);
  assert.equal(result.id, station.id);
  assert.deepEqual(result.payment_types, ['onnuri', 'incheon-eum']);
  assert.equal(result.verification.onnuri, station.verification.onnuri);
  assert.deepEqual(station.payment_types, ['onnuri']);
  assert.equal(regional.matches(result, 'local'), true);
  assert.equal(regional.matches(result, 'saengsaeng'), false);
  assert.deepEqual(regional.available([result]), ['incheon-eum']);
  assert.match(merchant.paymentSummary(result), /인천e음 카드/);
  assert.match(merchant.verificationText(result), /인천e음 조회: 2026-11-08/);
  assert.deepEqual(route.shortlist([result], {lat:37.44,lng:126.68}, {lat:37.48,lng:126.72}, 'incheon-eum','any'), [result]);
});

test('an unverified or wrong-region entry adds no station or regional option', () => {
  const invalid = [
    { ...entry, currency: 'saengsaeng' },
    { ...entry, verification: {...verification, status:'hold'} },
    { ...entry, verification: {...verification, channels:[]} },
    { ...entry, verification: {...verification, source_url:'javascript:alert(1)'} },
  ];
  assert.deepEqual(regional.mergeStations([station], invalid), [station]);
  assert.deepEqual(regional.available([station]), []);
});

test('a single dual-fuel station is included in both filters and routing', () => {
  const national = require('../assets/nationwide.js');
  const station = {
    id: 'dual', region: '강원', lat: 37.9, lng: 128.03, fuel_kind: 'dual',
    route_eligible: true, payment_types: ['gangwon-gift'],
    verification: {'gangwon-gift': {status: 'confirmed'}},
  };
  const state = {region: '강원', method: 'all', paymentScope: 'local'};
  const start = {lat: 37.8, lng: 128}, end = {lat: 38, lng: 128.1};
  for (const fuel of ['liquid', 'lpg']) {
    assert.equal(national.matches(station, {...state, fuel}), true);
    assert.deepEqual(route.shortlist([station], start, end, 'gangwon-gift', 'any', fuel), [station]);
  }
  assert.deepEqual(regional.fuelPrices(station), ['휘발유', '경유', 'LPG']);
});

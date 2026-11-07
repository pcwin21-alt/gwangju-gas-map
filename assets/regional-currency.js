(function (root) {
  'use strict';
  const products = {
    saengsaeng: { label: '광주 지역화폐', region: '광주', fill: '#285BB5', edge: '#173F86' },
    'incheon-eum': { label: '인천e음', region: '인천', fill: '#2AAFD4', edge: '#17495B', ink: '#0D3040' },
    'busan-dongbaek': { label: '동백전', region: '부산', fill: '#EE3C96', edge: '#8B0203', ink: '#3B0A29' },
    'gangwon-gift': { label: '강원상품권', region: '강원', fill: '#D83831', edge: '#7C1714' },
    'jeju-tamna': { label: '탐나는전', region: '제주', fill: '#FB8300', edge: '#713500', ink: '#381B06' },
    'daegu-ropay': { label: '대구로페이', region: '대구', fill: '#D80017', edge: '#770010' },
    'ulsan-pay': { label: '울산페이', region: '울산', fill: '#8E4599', edge: '#4B2052' },
    yeominjeon: { label: '여민전', region: '세종', fill: '#1F3383', edge: '#111F55' },
  };
  const channelLabels = { card: '카드', qr: 'QR', paper: '지류' };

  function product(id) {
    return Object.hasOwn(products, id) ? products[id] : null;
  }

  function localPayments(station) {
    return (station.payment_types || []).filter(id => product(id));
  }

  function matches(station, selection) {
    return selection === 'all' ||
      (selection === 'local' ? localPayments(station).length > 0 : (station.payment_types || []).includes(selection));
  }

  function label(selection) {
    return product(selection)?.label || { all: '전체', onnuri: '온누리', local: '지역화폐' }[selection] || '';
  }

  function available(stations) {
    const present = new Set(stations.flatMap(localPayments));
    return Object.keys(products).filter(id => present.has(id));
  }

  function channelText(station, id) {
    return (station.verification?.[id]?.channels || []).map(channel => channelLabels[channel]).filter(Boolean).join('·');
  }

  function mergeStations(base, entries) {
    const byId = new Map(base.map(station => [station.id, station]));
    for (const { stationId, station, currency, verification } of entries) {
      const scheme = product(currency);
      const existing = byId.get(stationId);
      if (!scheme || (existing || station)?.region !== scheme.region || verification?.status !== 'confirmed' ||
          !/^\d{4}-\d{2}-\d{2}/.test(verification.checked_at || '') ||
          !Array.isArray(verification.channels) || !verification.channels.length ||
          !verification.channels.every(channel => Object.hasOwn(channelLabels, channel)) ||
          !/^https:\/\//.test(verification.source_url || '')) continue;
      if (!existing && (!station || station.id !== stationId || !Number.isFinite(station.lat) || !Number.isFinite(station.lng))) continue;
      const record = existing || station;
      byId.set(stationId, {
        ...record,
        payment_types: [...new Set([...(record.payment_types || []), currency])],
        verification: { ...record.verification, [currency]: verification },
      });
    }
    return [...byId.values()];
  }

  function fuelMatches(station, selection) {
    return selection === 'all' || station.fuel_kind === selection ||
      (station.fuel_kind === 'dual' && (selection === 'liquid' || selection === 'lpg'));
  }

  function fuelPrices(station) {
    if (station.fuel_kind === 'dual') return ['휘발유', '경유', 'LPG'];
    return station.fuel_kind === 'lpg' ? ['LPG'] : ['휘발유', '경유'];
  }

  const api = { product, localPayments, matches, label, available, channelText, mergeStations, fuelMatches, fuelPrices };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GasRegionalCurrency = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);

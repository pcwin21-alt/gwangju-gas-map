(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GasPriceDisplay = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function effectivePrice(price, station) {
    if (typeof price !== 'number' || !Number.isFinite(price) || price <= 0) return null;
    return station?.payment_types?.includes('saengsaeng') ? Math.round(price * 9) / 10 : price;
  }
  function html(price, station) {
    const effective = effectivePrice(price, station);
    if (effective === null) return '';
    const format = value => value.toLocaleString('ko-KR', {maximumFractionDigits: 1});
    if (!station?.payment_types?.includes('saengsaeng')) return `<b>${format(price)}원/L</b>`;
    return `<span class="effective-price"><del aria-label="할인 전 단가">${format(price)}원/L</del> <b>${format(effective)}원/L</b><small>상생카드 10% 적용 체감가</small></span>`;
  }
  return {effectivePrice, html};
});

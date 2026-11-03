/* Keep information lookup usable when the external map SDK is unavailable. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const hasMap = () => Boolean(window.kakao?.maps);
  const dialog = document.createElement('dialog');
  dialog.id = 'tossStationDialog';
  dialog.className = 'toss-station-dialog';
  dialog.setAttribute('aria-labelledby', 'tossStationTitle');
  let returnFocus;
  const text = (tag, value, className) => {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    return node;
  };
  document.querySelector('.app').append(dialog);
  dialog.addEventListener('close', () => {
    (returnFocus?.isConnected ? returnFocus : byId('searchInput')).focus({preventScroll:true});
  });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  window.GasTossUI = {
    showStationDetails(station, trigger) {
      returnFocus = trigger;
      const heading = text('div', '', 'toss-station-heading');
      const title = text('h2', station.name);title.id = 'tossStationTitle';title.dataset.noI18n = '';
      const close = text('button', '닫기');close.type = 'button';close.setAttribute('aria-label', '주유소 상세 닫기');
      close.addEventListener('click', () => dialog.close());heading.append(title, close);
      const prices = GasStationResults.priceText(station, PRICES[station.id], PRICE_INFO[station.id]?.source_dates);
      const address = text('p', station.address || '상세주소 미확인');address.dataset.noI18n = '';
      dialog.replaceChildren(heading, address,
        text('p', GasMerchantDisplay.paymentSummary(station), 'toss-station-payment'),
        text('p', GasMerchantDisplay.verificationText(station) || '확인일 미확인', 'toss-station-note'),
        text('p', prices || '확보된 유가 정보가 없습니다.', 'toss-station-prices'),
        text('p', '자료 기준일 이후 가맹 상태와 가격이 바뀔 수 있습니다. 방문 전 해당 주유소에 확인하세요.', 'toss-station-note'));
      dialog.showModal();
    },
  };
  const search = byId('searchInput'), clear = byId('searchClear');
  search.addEventListener('input', () => {
    if (!hasMap()) clear.classList.toggle('visible', Boolean(search.value));
  });
  clear.addEventListener('click', () => {
    if (hasMap()) return;
    search.value = '';search.dispatchEvent(new Event('input', {bubbles:true}));search.focus();
  });
  // Capture runs before the shared reset handler recomputes regional results.
  byId('resetBtn').addEventListener('click', () => {
    if (hasMap()) return;
    search.value = '';search.dispatchEvent(new Event('input', {bubbles:true}));
    document.querySelector('.filter-btn[data-filter="all"]').click();
  }, true);
})();

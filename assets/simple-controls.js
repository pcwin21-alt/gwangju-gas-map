/* Progressive disclosure without changing the map's filter or URL state model. */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const toggle = byId('filtersToggle'), panel = byId('mapFilters');
  function sync() {
    const labels = [];
    const payment = document.querySelector('.filter-btn.active')?.dataset.filter;
    if (payment === 'onnuri') labels.push('온누리');
    if (payment === 'saengsaeng') labels.push('상생카드');
    const method = byId('onnuriMethod').value, fuel = byId('fuelSelect').value;
    if (method !== 'all') labels.push(method === 'paper' ? '지류' : '디지털');
    if (fuel !== 'all') labels.push(fuel === 'lpg' ? 'LPG' : '휘발유·경유');
    if (byId('districtSelect').value !== 'all') labels.push(byId('districtSelect').value);
    byId('filterCount').textContent = String(labels.length);
    byId('filterCount').hidden = !labels.length;
    byId('activeFilters').textContent = labels.join(' · ');
    byId('activeFilters').hidden = !labels.length;
  }
  toggle.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    toggle.setAttribute('aria-expanded', String(!panel.hidden));
  });
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      panel.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
  byId('filtersReset').addEventListener('click', () => {
    for (const id of ['onnuriMethod', 'fuelSelect', 'districtSelect']) {
      byId(id).value = 'all';
      byId(id).dispatchEvent(new Event('change', {bubbles:true}));
    }
    document.querySelector('.filter-btn[data-filter="all"]').click();
    sync();
  });
  document.querySelector('.controls').addEventListener('change', sync);
  document.querySelector('.controls').addEventListener('click', sync);
  byId('resetBtn').addEventListener('click', sync);
  window.addEventListener('popstate', sync);
  sync();
})();

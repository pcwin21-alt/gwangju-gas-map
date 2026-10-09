(() => {
  'use strict';
  const tools = document.getElementById('mapTools');
  const open = document.getElementById('toolsOpenBtn');
  const filters = [...document.querySelectorAll('.filter-btn')];
  const syncFilters = () => filters.forEach(button => button.setAttribute('aria-pressed', String(button.classList.contains('active'))));
  syncFilters();
  filters.forEach(button => button.addEventListener('click', syncFilters));
  document.getElementById('resetBtn').addEventListener('click', syncFilters);
  open.addEventListener('click', () => tools.showModal());
  document.getElementById('toolsHelpBtn').addEventListener('click', () => document.getElementById('helpBtn').click());
  document.getElementById('toolsCloseBtn').addEventListener('click', () => tools.close());
  // Close before existing action handlers open their own panels/dialogs.
  tools.querySelector('.tools-actions').addEventListener('click', event => {
    if (event.target.closest('button,a')) tools.close();
  }, true);
  tools.addEventListener('click', event => {
    if (event.target !== tools) return;
    const rect = tools.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) tools.close();
  });
  document.getElementById('updatesDialog').addEventListener('close', () => open.focus());
})();

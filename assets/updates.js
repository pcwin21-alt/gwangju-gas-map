(() => {
  'use strict';
  const dialog = document.getElementById('updatesDialog');
  const button = document.getElementById('updatesBtn');
  button.addEventListener('click', () => dialog.showModal());
  document.getElementById('updatesClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
})();

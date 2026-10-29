/* Apply before paint; storage failure must never prevent map use. */
(() => {
  'use strict';
  const query=window.matchMedia('(prefers-color-scheme: dark)');
  const valid=value=>['system','light','dark'].includes(value)?value:'system';
  let mode='system';
  try {mode=valid(localStorage.getItem('gas-map-theme'));} catch(_) {}
  function apply() {
    const theme=mode==='system'?(query.matches?'dark':'light'):mode;
    document.documentElement.dataset.theme=theme;
    document.documentElement.style.colorScheme=theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme==='dark'?'#111d2e':'#ffffff');
    window.dispatchEvent(new CustomEvent('gas:themechange',{detail:{theme,mode}}));
  }
  function setMode(value) {mode=valid(value);try {localStorage.setItem('gas-map-theme',mode);}catch(_){}apply();}
  query.addEventListener('change',()=>{if(mode==='system')apply();});
  window.addEventListener('storage',event=>{if(event.key==='gas-map-theme'){mode=valid(event.newValue);apply();const select=document.getElementById('themeMode');if(select)select.value=mode;}});
  document.addEventListener('DOMContentLoaded',()=>{
    const select=document.getElementById('themeMode');select.value=mode;
    select.addEventListener('change',()=>setMode(select.value));
  });
  apply();
})();

(() => {
  'use strict';
  const byId=id=>document.getElementById(id),panel=byId('tripPanel'),launcher=byId('tripLauncher'),opacity=byId('tripOpacity');
  const area=document.querySelector('.map-area');
  function sync() {
    launcher.hidden=panel.open;launcher.setAttribute('aria-expanded',String(panel.open));
    if(!panel.open&&panel.contains(document.activeElement)){document.activeElement.blur();launcher.focus({preventScroll:true});}
  }
  function minimize(focus=false) {
    if(panel.contains(document.activeElement))document.activeElement.blur();
    panel.open=false;sync();if(focus)launcher.focus({preventScroll:true});
  }
  function open() {panel.open=true;sync();panel.querySelector('summary').focus({preventScroll:true});}
  launcher.addEventListener('click',open);panel.addEventListener('toggle',sync);
  byId('expandMapBtn').addEventListener('click',()=>minimize());
  function mapGesture(event) {if(!panel.open||event.target.closest('#tripPanel,#tripLauncher'))return;minimize();}
  area.addEventListener('pointerdown',mapGesture,{capture:true,passive:true});
  area.addEventListener('touchstart',mapGesture,{capture:true,passive:true});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel.open&&!document.activeElement.closest?.('dialog[open]'))minimize(true);});
  function paint() {
    const alpha=['1','0.9','0.75'].includes(opacity.value)?opacity.value:'1';
    const hex=getComputedStyle(document.documentElement).getPropertyValue('--panel').trim();
    const rgb=/^#[\da-f]{6}$/i.test(hex)?[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)):[255,255,255];
    panel.style.setProperty('--trip-surface',`rgba(${rgb.join(',')},${alpha})`);
  }
  try {const saved=localStorage.getItem('gas-trip-opacity');if(['1','0.9','0.75'].includes(saved))opacity.value=saved;}catch{}
  opacity.addEventListener('change',()=>{paint();try{localStorage.setItem('gas-trip-opacity',opacity.value);}catch{}});
  window.addEventListener('gas:themechange',paint);
  const results=byId('tripResults');
  new MutationObserver(()=>{const count=results.querySelectorAll('.trip-result').length;byId('tripLauncherCount').textContent=String(count);byId('tripLauncherCount').hidden=!count;launcher.setAttribute('aria-label',count?`경유 주유소 찾기 열기, 추천 ${count}곳`:'경유 주유소 찾기 열기');}).observe(results,{childList:true});
  window.GasTripWindow={open,minimize};paint();sync();
})();

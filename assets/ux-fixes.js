/* Shared keyboard dismissal for the existing secondary sheets. */
(() => {
  'use strict';
  const definitions=[['helpModal','helpModalClose','사용법 안내'],['coffeeModal','coffeeModalClose','커피 사주기'],['rankModal','rankModalClose','가격 순위'],['nearbyPanel','nearbyPanelClose','주변 내보내기'],['reportPanel','reportPanelClose','제보'],['reactPanel','reactPanelClose','반응 남기기']];
  const layers=definitions.map(([id,closeId,label])=>({node:document.getElementById(id),close:document.getElementById(closeId),label})).filter(l=>l.node&&l.close);
  let current=null,restore=null;
  function sync(){
    const opened=layers.find(l=>l.node.classList.contains('open'));
    if(opened===current)return;
    if(opened){restore=document.activeElement;current=opened;opened.node.setAttribute('role','dialog');opened.node.setAttribute('aria-modal','true');opened.node.setAttribute('aria-label',opened.label);opened.close.focus({preventScroll:true});}
    else{current=null;const target=restore&&restore.getClientRects().length?restore:document.getElementById('toolsOpenBtn');target?.focus({preventScroll:true});restore=null;}
  }
  const observer=new MutationObserver(sync);for(const layer of layers)observer.observe(layer.node,{attributes:true,attributeFilter:['class']});
  document.addEventListener('keydown',event=>{
    if(event.isComposing||document.querySelector('dialog[open]'))return;
    if(current){
      if(event.key==='Escape'){event.preventDefault();current.close.click();return;}
      if(event.key==='Tab'){
        const controls=[...current.node.querySelectorAll('button,a[href],input,select,textarea,[tabindex="0"]')].filter(el=>!el.disabled&&el.getClientRects().length);
        const first=controls[0],last=controls.at(-1);if(!first)return;
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
      }
    }else if(event.key==='Escape'&&typeof activeOverlay!=='undefined'&&activeOverlay){event.preventDefault();closeStationOverlay(true);}
  });
})();

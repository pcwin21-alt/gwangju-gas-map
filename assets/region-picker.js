/* Reuse the existing region selection and filter pipeline inside a modal. */
(() => {
  'use strict';
  const byId=id=>document.getElementById(id),input=byId('regionSelect'),dialog=byId('regionDialog'),open=byId('regionOpen');
  const buttons=new Map();
  for(const value of ['광주','all',...GasNational.regions.filter(name=>name!=='광주')]) {
    const button=document.createElement('button');button.type='button';button.textContent=value==='all'?'전국':value;
    button.dataset.region=value;buttons.set(value,button);
    button.addEventListener('click',()=>{
      if(input.value!==value){input.value=value;input.dispatchEvent(new Event('change',{bubbles:true}));}
      sync();dialog.close();
    });
    byId('regionOptions').append(button);
  }
  function sync() {
    const label=input.value==='all'?'전국':input.value;
    byId('regionLabel').textContent=label;open.setAttribute('aria-label','지역 선택, '+label);
    for(const [value,button] of buttons)button.setAttribute('aria-pressed',String(value===input.value));
  }
  open.addEventListener('click',()=>{sync();dialog.showModal();buttons.get(input.value)?.focus({preventScroll:true});});
  byId('regionClose').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('keydown',event=>{
    if(event.key!=='Tab')return;
    const first=byId('regionClose'),last=[...buttons.values()].at(-1);
    if(!event.shiftKey&&event.target===last){event.preventDefault();first.focus();}
    if(event.shiftKey&&event.target===first){event.preventDefault();last.focus();}
  });
  dialog.addEventListener('click',event=>{
    if(event.target!==dialog)return;
    const r=dialog.getBoundingClientRect();
    if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();
  });
  dialog.addEventListener('close',()=>open.focus({preventScroll:true}));
  input.addEventListener('change',sync);byId('resetBtn').addEventListener('click',sync);window.addEventListener('popstate',sync);sync();
})();

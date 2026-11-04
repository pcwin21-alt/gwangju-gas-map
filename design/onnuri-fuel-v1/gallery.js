/* Interactions in the component gallery are local examples only. */
(() => {
  if(new URL(location.href).searchParams.get('text')==='large')document.documentElement.style.fontSize='200%';
  const dialog=document.getElementById('componentDialog'),body=document.getElementById('dialogBody');
  let returnFocus=null,toastTimer;
  const toast=value=>{const node=document.getElementById('demoToast');node.textContent=value;node.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{node.hidden=true;},2400);};
  document.getElementById('sheetTheme').addEventListener('change',event=>{document.documentElement.dataset.theme=event.target.value;});
  dialog.addEventListener('close',()=>returnFocus?.focus({preventScroll:true}));
  document.addEventListener('click',event=>{
    const target=event.target.closest('button');if(!target)return;
    if(target.dataset.filterGroup){const group=target.dataset.filterGroup;document.querySelectorAll('[data-filter-group]').forEach(b=>b.setAttribute('aria-pressed',String(b===target)));document.querySelectorAll('.component').forEach(x=>{x.hidden=group!=='all'&&x.dataset.group!==group;});}
    if(target.hasAttribute('data-demo-detail')){returnFocus=target;body.replaceChildren(document.getElementById('template-detail').content.cloneNode(true));if(!dialog.open)dialog.showModal();}
    if(target.dataset.demoOpen){returnFocus=target;body.replaceChildren(document.getElementById('template-'+target.dataset.demoOpen).content.cloneNode(true));if(!dialog.open)dialog.showModal();}
    if(target.hasAttribute('data-dialog-close')||target.hasAttribute('data-demo-close')){if(dialog.open)dialog.close();}
    const single=target.closest('[data-demo-segments],[data-demo-single]');if(single){single.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===target)));}
    if(target.hasAttribute('data-demo-clear')){const search=target.closest('.fu-search').querySelector('input');search.value='';search.focus();}
    if(target.hasAttribute('data-location-demo')){toast('시안에서는 위치를 요청하지 않아요. 지역·주소 검색을 이용해 주세요.');}
    if(target.hasAttribute('data-pagination-demo')){target.parentElement.querySelector('[data-pagination-result]').textContent='이 시트는 추가 보기의 디자인 예시예요.';}
    if(target.hasAttribute('data-demo-reset')){target.closest('.demo,#dialogBody').querySelectorAll('select').forEach(x=>{x.selectedIndex=0;});toast('선택한 조건을 초기화했어요');}
    if(target.dataset.demoToast)toast(target.dataset.demoToast);
  });
})();

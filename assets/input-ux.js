/* Keep editing tied to explicit input actions; map gestures never focus a field. */
(() => {
  'use strict';
  const editable = el => !el?.readOnly && !el?.disabled && el?.matches?.('input:not([type="checkbox"]):not([type="radio"]):not([type="button"]):not([type="submit"]):not([type="file"]),textarea,[contenteditable="true"]');
  function dismiss() {
    if (editable(document.activeElement)) document.activeElement.blur();
  }
  const map = document.querySelector('.map-area');
  const gesture = event => {
    if (event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
    dismiss(); // Do not cancel the event: Kakao must receive the original pan/pinch gesture.
  };
  map.addEventListener('pointerdown', gesture, {capture:true,passive:true});
  map.addEventListener('touchstart', gesture, {capture:true,passive:true});
  for (const id of ['tripPanel','tripSettings','tripCriteria']) {
    const panel=document.getElementById(id);
    panel.addEventListener('toggle',()=>{if(!panel.open && panel.contains(document.activeElement)) dismiss();});
  }
  // Close the keyboard when an explicit non-editing action leaves a text field.
  document.addEventListener('click', event => {
    const action=event.target.closest('button,summary,a');
    if (!action || action.id==='searchClear') return;
    dismiss();
  }, {capture:true});
  const viewport=window.visualViewport;
  let restingHeight=window.innerHeight,restingWidth=window.innerWidth;
  function revealInput() {
    const input=document.activeElement;
    if (!editable(input)) return;
    const scroller=input.closest?.('.trip-body,.report-panel-box,.react-panel-box');
    if (!scroller) return;
    const field=input.getBoundingClientRect(), bounds=scroller.getBoundingClientRect();
    const top=Math.max(bounds.top,viewport?.offsetTop||0),bottom=Math.min(bounds.bottom,(viewport?.offsetTop||0)+(viewport?.height||window.innerHeight));
    if (field.bottom>bottom-12) scroller.scrollTop+=field.bottom-bottom+12;
    else if (field.top<top+12) scroller.scrollTop-=top+12-field.top;
  }
  function resize() {
    if (viewport && viewport.scale !== 1) return; // Preserve browser pinch zoom.
    if(Math.abs(window.innerWidth-restingWidth)>80){restingWidth=window.innerWidth;restingHeight=window.innerHeight;}
    else if(!editable(document.activeElement))restingHeight=Math.max(restingHeight,window.innerHeight);
    const height=viewport?.height || window.innerHeight;
    document.documentElement.style.setProperty('--app-height',`${Math.round(height)}px`);
    document.documentElement.classList.toggle('keyboard-open',!!editable(document.activeElement) && restingHeight-height>100);
    requestAnimationFrame(revealInput);
  }
  viewport?.addEventListener('resize',resize);
  viewport?.addEventListener('scroll',()=>requestAnimationFrame(revealInput));
  window.addEventListener('resize',resize);
  document.addEventListener('focusin',resize);
  document.addEventListener('focusout',()=>requestAnimationFrame(resize));
  // Enter = finish the station filter; composition Enter only commits Korean text.
  document.getElementById('searchInput').addEventListener('keydown',event=>{
    if(event.key==='Enter' && !event.isComposing && event.keyCode!==229){event.preventDefault();dismiss();}
  });
  resize();
})();

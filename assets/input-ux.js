/* Keep editing tied to explicit input actions; map gestures never focus a field. */
(() => {
  'use strict';
  const editable = el => el?.matches?.('input:not([type="checkbox"]):not([type="radio"]):not([type="button"]):not([type="submit"]):not([type="file"]),textarea,[contenteditable="true"]');
  function dismiss() {
    if (editable(document.activeElement)) document.activeElement.blur();
  }
  const map = document.getElementById('map');
  const gesture = event => {
    if (event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
    dismiss(); // Do not cancel the event: Kakao must receive the original pan/pinch gesture.
  };
  map.addEventListener('pointerdown', gesture, {capture:true,passive:true});
  if (!window.PointerEvent) map.addEventListener('touchstart', gesture, {capture:true,passive:true});
  for (const id of ['tripPanel','tripSettings']) {
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
  function resize() {
    if (viewport && viewport.scale !== 1) return; // Preserve browser pinch zoom.
    const height=viewport?.height || window.innerHeight;
    document.documentElement.style.setProperty('--app-height',`${Math.round(height)}px`);
    document.documentElement.classList.toggle('keyboard-open',!!editable(document.activeElement) && window.innerHeight-height>100);
  }
  viewport?.addEventListener('resize',resize);
  window.addEventListener('resize',resize);
  document.addEventListener('focusin',resize);
  document.addEventListener('focusout',()=>requestAnimationFrame(resize));
  // Enter = finish the station filter; composition Enter only commits Korean text.
  document.getElementById('searchInput').addEventListener('keydown',event=>{
    if(event.key==='Enter' && !event.isComposing && event.keyCode!==229){event.preventDefault();dismiss();}
  });
  resize();
})();

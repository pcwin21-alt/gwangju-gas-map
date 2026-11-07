/* Shared web-review/Toss candidate pins. Orange sampled from official onnuri.gift header SVG, 2026-11-05.
   Companion shades and regional adaptations are our design choices. */
const FUEL_PIN_THEMES = {
  onnuri: {key:'onnuri',label:'온누리',fill:'#EB6620',edge:'#8D350C',ink:'#351607',surface:'var(--fuel-brand-soft)',priceInk:'var(--fuel-primary)',priceEdge:'var(--fuel-pin-border)',symbol:'circle'},
  currencies: {
    'gwangju-saengsaeng': {key:'gwangju-saengsaeng',label:'광주 지역화폐',fill:'#285BB5',edge:'#173F86',ink:'#FFFFFF',surface:'var(--fuel-currency-soft)',priceInk:'var(--fuel-currency-ink)',priceEdge:'var(--fuel-currency-ink)',symbol:'diamond',source:'https://www.gwangju.go.kr/economy/contentsView.do?pageId=economy122'}
  },
  unknown: {key:'local-unassigned',label:'지역화폐',fill:'#596673',edge:'#34404C',ink:'#FFFFFF',surface:'#F0F3F5',symbol:'diamond'}
};
function fuelPinTheme(station,payment='all'){
  const types=station.payment_types||[],onnuri=types.includes('onnuri');
  const localIds=GasRegionalCurrency.localPayments(station);
  const chosen=localIds.includes(payment)?payment:localIds[0];
  const local=Boolean(chosen), product=GasRegionalCurrency.product(chosen);
  const currencyId=station.local_currency_id||(station.region==='광주'?'gwangju-saengsaeng':null);
  const regional=chosen==='saengsaeng'?(FUEL_PIN_THEMES.currencies[currencyId]||FUEL_PIN_THEMES.unknown):
    product?{...product,key:chosen,ink:product.ink||'#FFF',surface:'var(--fuel-currency-soft)',priceInk:'var(--fuel-ink)',priceEdge:product.edge,symbol:'diamond'}:FUEL_PIN_THEMES.unknown;
  if(payment==='onnuri'&&onnuri)return FUEL_PIN_THEMES.onnuri;
  if(local&&(payment==='local'||localIds.includes(payment)))return regional;
  if(onnuri&&local)return {key:'both-'+regional.key,label:'온누리 + '+regional.label,fill:FUEL_PIN_THEMES.onnuri.fill,second:regional.fill,edge:'#34404C',ink:'#351607',priceInk:'var(--fuel-ink)',priceEdge:'var(--fuel-control-line)',surface:'linear-gradient(110deg,var(--fuel-brand-soft) 50%,'+regional.surface+' 50%)',symbol:'double'};
  return local?regional:FUEL_PIN_THEMES.onnuri;
}
function fuelPinSvg(theme){
  const path='M14 1C6.82 1 1 6.82 1 14c0 9.8 13 21 13 21s13-11.2 13-21C27 6.82 21.18 1 14 1z';
  const split=theme.second?`<path d="${path}" fill="${theme.second}" clip-path="url(#right)"/>`:'';
  const symbol=theme.symbol==='diamond'?`<path d="m14 8 6 6-6 6-6-6z" fill="${theme.ink}"/>`:theme.symbol==='double'?'<circle cx="10" cy="14" r="3" fill="#351607"/><circle cx="18" cy="14" r="3" fill="#FFF"/>':`<circle cx="14" cy="14" r="4.5" fill="${theme.ink}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36"><defs><clipPath id="right"><rect x="14" width="14" height="36"/></clipPath></defs><path d="${path}" fill="${theme.fill}"/>${split}<path d="${path}" fill="none" stroke="${theme.edge}" stroke-width="1.6"/><path d="M14 .4C6.5.4.4 6.5.4 14c0 10.1 13.6 21.8 13.6 21.8S27.6 24.1 27.6 14C27.6 6.5 21.5.4 14 .4Z" fill="none" stroke="#FFF" stroke-width=".8"/>${symbol}</svg>`;
}

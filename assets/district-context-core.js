(function(root){
  'use strict';
  function segmentDistance(p,a,b) {
    const dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;
    const t=den?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)):0;
    return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy);
  }
  function inRing(point,ring) {
    let inside=false;
    for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
      const a=ring[j],b=ring[i];
      if(segmentDistance(point,a,b)<1e-7)return true;
      if((a[1]>point[1])!==(b[1]>point[1])&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;
    }
    return inside;
  }
  const contains=(p,polygons)=>polygons.some(rings=>inRing(p,rings[0])&&!rings.slice(1).some(hole=>inRing(p,hole)));
  function boundaryDistance(point,polygons) {
    let distance=Infinity;
    for(const rings of polygons)for(const ring of rings)for(let i=0,j=ring.length-1;i<ring.length;j=i++)distance=Math.min(distance,segmentDistance(point,ring[j],ring[i]));
    return distance;
  }
  function anchor(polygons,width,height) {
    let best=null,bestScore=-Infinity;
    const left=42,right=width-42,top=64,bottom=height-88;
    if(right<=left||bottom<=top)return null;
    for(let y=0;y<=12;y++)for(let x=0;x<=12;x++) {
      const p=[left+(right-left)*x/12,top+(bottom-top)*y/12];
      if(![[0,0],[-36,-18],[36,-18],[-36,18],[36,18]].every(([dx,dy])=>contains([p[0]+dx,p[1]+dy],polygons)))continue;
      const score=Math.min(boundaryDistance(p,polygons),70)-.12*Math.hypot(p[0]-width/2,p[1]-height/2);
      if(score>bestScore){best=p;bestScore=score;}
    }
    return best;
  }
  function context(features,width,height,threshold=110) {
    const center=[width/2,height/2];
    const entries=features.map(f=>({...f,inside:contains(center,f.polygons),distance:boundaryDistance(center,f.polygons)}));
    const home=entries.find(e=>e.inside);
    if(home&&home.distance>threshold)return {home:null,neighbors:[],labels:[]};
    const neighbors=entries.filter(e=>e!==home&&e.distance<=threshold).sort((a,b)=>a.distance-b.distance).slice(0,2);
    const nearby=home?[home,...neighbors]:neighbors;
    return {home:home?.name||null,neighbors:neighbors.map(e=>e.name),labels:nearby.map(e=>({name:e.name,point:anchor(e.polygons,width,height)})).filter(e=>e.point)};
  }
  const api={contains,boundaryDistance,anchor,context};
  if(typeof module!=='undefined')module.exports=api;
  root.GasDistrictContextCore=api;
})(typeof window==='undefined'?globalThis:window);

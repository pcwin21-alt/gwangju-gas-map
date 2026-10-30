/* Keep the SDK's drawing area in sync with responsive layout changes. */
(function(root) {
  'use strict';
  function create(map, container, getPoints, sdk = root.kakao.maps) {
    let frame = 0;
    function fit() {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if(root.GasRouteMap?.isActive()){root.GasRouteMap.fit();return;}
        const points = getPoints().filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lng));
        if (!points.length || !container.clientWidth || !container.clientHeight) return;
        map.relayout();
        if (points.length === 1) {
          map.setCenter(new sdk.LatLng(points[0].lat, points[0].lng));
          map.setLevel(4);
          return;
        }
        const bounds = new sdk.LatLngBounds();
        points.forEach(p => bounds.extend(new sdk.LatLng(p.lat, p.lng)));
        map.setBounds(bounds, Math.min(32, Math.round(container.clientHeight * .15)),
          28, Math.min(82, Math.round(container.clientHeight * .22)), 28);
      });
    }
    let resizeFrame = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => {
        if (!container.clientWidth || !container.clientHeight) return;
        const center = map.getCenter();
        map.relayout();
        map.setCenter(center);
        // Resize only the drawing surface. Rotation and browser chrome must not
        // undo the user's zoom or pan; fit only for explicit result navigation.
      });
    });
    observer.observe(container);
    return {fit,cancelFit:()=>cancelAnimationFrame(frame)};
  }
  root.GasMapViewport = {create};
})(typeof globalThis !== 'undefined' ? globalThis : this);

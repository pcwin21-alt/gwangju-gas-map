/* Keep the SDK's drawing area in sync with responsive layout changes. */
(function(root) {
  'use strict';
  function create(map, container, getPoints, sdk = root.kakao.maps) {
    let frame = 0, width = container.clientWidth;
    function fit() {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
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
        map.setBounds(bounds, Math.min(96, Math.round(container.clientHeight * .22)),
          28, Math.min(36, Math.round(container.clientHeight * .1)), 28);
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
        // Orientation/width changes need a new fit; height changes retain the view.
        if (width !== container.clientWidth) fit();
        width = container.clientWidth;
      });
    });
    observer.observe(container);
    return {fit};
  }
  root.GasMapViewport = {create};
})(typeof globalThis !== 'undefined' ? globalThis : this);

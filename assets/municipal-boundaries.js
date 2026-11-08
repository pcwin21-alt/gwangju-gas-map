(() => {
  'use strict';
  if (!window.kakao?.maps || typeof map === 'undefined') return;

  const dataUrl = document.currentScript.dataset.src;
  const line = new kakao.maps.Polyline({
    path: [],
    strokeWeight: 2,
    strokeColor: '#504d73',
    strokeOpacity: 0.66,
    strokeStyle: 'shortdash',
    zIndex: 0,
  });
  let borders;
  let loading = false;
  let retryAfter = 0;
  let previousPaths = [];

  async function loadBorders() {
    loading = true;
    try {
      const response = await fetch(dataUrl);
      if (!response.ok) throw new Error(`Boundary data returned HTTP ${response.status}`);
      const data = await response.json();
      borders = data.lines.map(([bounds, coordinates]) => ({ bounds, coordinates }));
    } catch {
      retryAfter = Date.now() + 30_000;
    } finally {
      loading = false;
    }
    if (borders) update();
  }

  function update() {
    if (map.getLevel() > MUNICIPAL_BOUNDARY_MAX_LEVEL) {
      if (line.getMap()) line.setMap(null);
      return;
    }
    if (!borders) {
      if (!loading && Date.now() >= retryAfter) void loadBorders();
      return;
    }
    const bounds = map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    const west = sw.getLng();
    const south = sw.getLat();
    const east = ne.getLng();
    const north = ne.getLat();
    const paths = [];
    for (const border of borders) {
      const [left, bottom, right, top] = border.bounds;
      if (left > east || right < west || bottom > north || top < south) continue;
      border.path ??= border.coordinates.map(([lng, lat]) => new kakao.maps.LatLng(lat, lng));
      paths.push(border.path);
    }
    if (!paths.length) {
      if (line.getMap()) line.setMap(null);
      return;
    }
    if (paths.length !== previousPaths.length || paths.some((path, i) => path !== previousPaths[i])) {
      line.setPath(paths);
      previousPaths = paths;
    }
    if (!line.getMap()) line.setMap(map);
  }

  kakao.maps.event.addListener(map, 'zoom_changed', update);
  kakao.maps.event.addListener(map, 'idle', update);
  update();
})();

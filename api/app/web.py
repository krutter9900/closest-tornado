from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Closest Tornado</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    :root {
      --bg: #0b1220;
      --card: rgba(16, 26, 47, 0.85);
      --text: #e7edf7;
      --muted: #9fb0cc;
      --accent: #5aa5ff;
      --accent-2: #7dd3fc;
      --border: rgba(159, 176, 204, 0.22);
      --shadow: 0 14px 38px rgba(0, 0, 0, 0.35);
      --danger: #ff6b6b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      background: radial-gradient(circle at 20% -10%, #1b2b52 0%, #0b1220 45%, #060b16 100%);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
    }
    .shell { display: grid; grid-template-columns: 390px minmax(0, 1fr); gap: 14px; padding: 14px; min-height: 100vh; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; backdrop-filter: blur(8px); box-shadow: var(--shadow); }
    .sidebar { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
    .title { margin: 0; font-size: 1.28rem; }
    .subtitle { margin: 0; color: var(--muted); font-size: 0.9rem; line-height: 1.4; }
    label { color: var(--muted); font-size: 0.78rem; display: block; margin: 0 0 6px; letter-spacing: .35px; text-transform: uppercase; }
    .field, .select, .button { width: 100%; border-radius: 11px; border: 1px solid var(--border); font-size: 0.95rem; }
    .field, .select { background: #0f1930; color: var(--text); padding: 11px 12px; }
    .controls { display: grid; grid-template-columns: 1fr 120px; gap: 8px; }
    .button { cursor: pointer; border: none; font-weight: 600; color: white; padding: 11px 14px; background: linear-gradient(135deg, var(--accent), var(--accent-2)); }
    .button:disabled { filter: grayscale(0.35) brightness(0.8); cursor: default; }
    .panel { background: rgba(7, 13, 25, 0.72); border: 1px solid var(--border); border-radius: 12px; padding: 12px; }
    .status { margin: 0; color: var(--muted); font-size: 0.84rem; }
    .share-wrap { display: flex; gap: 8px; margin-top: 8px; }
    .share-link { flex: 1; min-width: 0; font-size: 0.8rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border: 1px dashed var(--border); border-radius: 8px; padding: 8px; }
    .copy-btn { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; background: #14203a; color: var(--text); cursor: pointer; }
    .results { display: grid; gap: 8px; max-height: 330px; overflow: auto; }
    .result-item { border: 1px solid var(--border); border-radius: 10px; padding: 9px; background: rgba(13, 20, 36, 0.85); cursor: pointer; }
    .result-item.active { border-color: #5aa5ff; box-shadow: 0 0 0 2px rgba(90,165,255,.2); }
    .line1 { margin: 0; font-weight: 600; font-size: 0.92rem; }
    .line2 { margin: 2px 0 0; color: var(--muted); font-size: 0.82rem; }
    .error { color: var(--danger); font-weight: 600; }
    .map-wrap { position: relative; overflow: hidden; min-height: calc(100vh - 28px); }
    #map { position: absolute; inset: 0; }
    .legend {
      position: absolute; left: 14px; bottom: 14px; z-index: 4;
      background: rgba(6, 12, 24, 0.84); border: 1px solid var(--border); border-radius: 10px;
      padding: 8px 10px; font-size: 12px; color: var(--muted);
    }
    .legend-row { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
    .swatch { width: 12px; height: 12px; border-radius: 999px; border: 1px solid rgba(255,255,255,.6); }
    .sw-line { width: 16px; height: 4px; border-radius: 6px; background: #4f9cff; }
    .sw-corridor { width: 16px; height: 10px; border-radius: 4px; background: rgba(249, 115, 22, 0.25); border: 1px solid rgba(249, 115, 22, .6); }
    @media (max-width: 980px) {
      .shell { grid-template-columns: 1fr; min-height: auto; }
      .controls { grid-template-columns: 1fr; }
      .map-wrap { min-height: 62vh; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="card sidebar">
      <div>
        <h1 class="title">Closest Tornado</h1>
        <p class="subtitle">Find the nearest tornado tracks, compare the top 5, and share a privacy-safe link using only coordinates.</p>
      </div>

      <div>
        <label for="addr">Address</label>
        <input id="addr" class="field" placeholder="123 N Robinson Ave, Oklahoma City, OK 73102" />
      </div>

      <div class="controls">
        <div>
          <label for="units">Units</label>
          <select id="units" class="select" aria-label="Units">
            <option value="miles" selected>Miles</option>
            <option value="km">Kilometers</option>
          </select>
        </div>
        <div style="display:flex; align-items:flex-end;">
          <button id="go" class="button">Find</button>
        </div>
      </div>

      <section class="panel">
        <p class="status" id="status">Ready. Enter an address or open a shared link.</p>
        <div class="share-wrap" id="shareWrap" style="display:none;">
          <div class="share-link" id="shareLink"></div>
          <button class="copy-btn" id="copyBtn">Copy</button>
        </div>
      </section>

      <section class="panel">
        <label style="margin-top:0">Top 5 closest tornadoes</label>
        <div class="results" id="resultsList">
          <div class="status">No results yet.</div>
        </div>
      </section>
    </section>

    <section class="card map-wrap">
      <div id="map"></div>
      <div class="legend">
        <div class="legend-row"><span class="swatch" style="background:#22c55e"></span>User point</div>
        <div class="legend-row"><span class="swatch" style="background:#f97316"></span>Closest point</div>
        <div class="legend-row"><span class="sw-line" style="background:#3b82f6"></span>Other top-5 tracks</div>
        <div class="legend-row"><span class="sw-line" style="background:#60a5fa; height:6px;"></span>Selected track</div>
        <div class="legend-row"><span class="sw-corridor"></span>Damage path corridor</div>
      </div>
    </section>
  </div>

  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const statusEl = document.getElementById('status');
    const addr = document.getElementById('addr');
    const btn = document.getElementById('go');
    const units = document.getElementById('units');
    const list = document.getElementById('resultsList');
    const shareWrap = document.getElementById('shareWrap');
    const shareLinkEl = document.getElementById('shareLink');
    const copyBtn = document.getElementById('copyBtn');

    let latestPayload = null;
    let selectedIndex = 0;

    const map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
      center: [-97.5164, 35.4676],
      zoom: 10
    });
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'imperial' }), 'bottom-right');

    function resetLayers() {
      for (const id of ['corridor-outline', 'corridor', 'tracks', 'closest', 'user']) {
        if (map.getLayer(id)) map.removeLayer(id);
        if (map.getSource(id)) map.removeSource(id);
      }
    }

    function renderShare(url) {
      shareWrap.style.display = 'flex';
      shareLinkEl.textContent = url;
      shareLinkEl.title = url;
    }

    function renderList(payload) {
      const items = payload.top_results || [];
      if (!items.length) {
        list.innerHTML = '<div class="status">No nearby events found.</div>';
        return;
      }

      list.innerHTML = items.map((item, idx) => `
        <div class="result-item ${idx === selectedIndex ? 'active' : ''}" data-idx="${idx}">
          <p class="line1">${item.selected_distance.toFixed(3)} ${item.selected_unit} · ${item.tor_f_scale || 'Unknown scale'}</p>
          <p class="line2">${item.begin_dt || 'Unknown date'} · ${item.cz_name || ''} ${item.state || ''}</p>
        </div>
      `).join('');

      list.querySelectorAll('.result-item').forEach(el => {
        el.addEventListener('click', () => {
          selectedIndex = Number(el.dataset.idx);
          renderList(payload);
          renderSelection();
        });
      });
    }

    function renderSelection() {
      if (!latestPayload) return;
      const q = latestPayload.query;
      const selected = latestPayload.top_results[selectedIndex];
      if (!selected) return;

      statusEl.innerHTML = selected
        ? `Showing <strong>${selected.selected_distance.toFixed(3)} ${selected.selected_unit}</strong> (${selected.distance_type.replaceAll('_', ' ')})${selected.corridor_geojson ? '' : ' · corridor unavailable for this event'}`
        : 'No selection';

      resetLayers();

      if (selected.corridor_geojson) {
        map.addSource('corridor', { type: 'geojson', data: { type: 'Feature', geometry: selected.corridor_geojson }});
        map.addLayer({
          id: 'corridor',
          type: 'fill',
          source: 'corridor',
          paint: { 'fill-color': '#f97316', 'fill-opacity': 0.35 }
        });
        map.addLayer({
          id: 'corridor-outline',
          type: 'line',
          source: 'corridor',
          paint: { 'line-color': '#fb923c', 'line-width': 2, 'line-opacity': 0.95 }
        });
      }

      const tracks = latestPayload.top_results
        .filter(item => item.track_geojson)
        .map((item, idx) => ({
          type: 'Feature',
          properties: {
            idx,
            isSelected: idx === selectedIndex
          },
          geometry: item.track_geojson
        }));

      map.addSource('tracks', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: tracks
        }
      });
      map.addSource('closest', { type: 'geojson', data: { type: 'Feature', geometry: selected.closest_point_geojson }});
      map.addSource('user', { type: 'geojson', data: { type: 'Feature', geometry: { type: 'Point', coordinates: [q.lon, q.lat] }}});

      map.addLayer({
        id: 'tracks',
        type: 'line',
        source: 'tracks',
        paint: {
          'line-width': ['case', ['boolean', ['get', 'isSelected'], false], 6, 3],
          'line-color': ['case', ['boolean', ['get', 'isSelected'], false], '#60a5fa', '#3b82f6'],
          'line-opacity': ['case', ['boolean', ['get', 'isSelected'], false], 0.98, 0.5]
        }
      });
      map.addLayer({ id: 'closest', type: 'circle', source: 'closest', paint: { 'circle-radius': 7, 'circle-color': '#f97316', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }});
      map.addLayer({ id: 'user', type: 'circle', source: 'user', paint: { 'circle-radius': 7, 'circle-color': '#22c55e', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }});

      const coords = tracks.flatMap(feature => feature.geometry.coordinates);
      coords.push([q.lon, q.lat]);
      const bounds = coords.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0]));
      map.fitBounds(bounds, { padding: 72, maxZoom: 14, duration: 700 });
    }

    async function loadFromAddress() {
      const address = addr.value.trim();
      const selectedUnits = units.value;
      if (!address) return;

      btn.disabled = true;
      statusEl.textContent = 'Searching by address…';
      try {
        const res = await fetch('/closest-tornado', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ address, units: selectedUnits })
        });
        const data = await res.json();
        if (!res.ok) {
          statusEl.innerHTML = `<span class="error">${data.detail || 'Request failed'}</span>`;
          return;
        }

        latestPayload = data;
        selectedIndex = 0;
        renderShare(data.share_url);
        renderList(data);
        renderSelection();
      } catch (err) {
        statusEl.innerHTML = '<span class="error">Could not complete request.</span>';
      } finally {
        btn.disabled = false;
      }
    }

    async function loadFromShare(lat, lon, selectedUnits) {
      btn.disabled = true;
      units.value = selectedUnits;
      statusEl.textContent = 'Loading shared link…';
      try {
        const res = await fetch(`/closest-tornado-by-coords?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&units=${encodeURIComponent(selectedUnits)}`);
        const data = await res.json();
        if (!res.ok) {
          statusEl.innerHTML = `<span class="error">${data.detail || 'Shared lookup failed'}</span>`;
          return;
        }
        latestPayload = data;
        selectedIndex = 0;
        renderShare(data.share_url);
        renderList(data);
        renderSelection();
      } catch (err) {
        statusEl.innerHTML = '<span class="error">Could not load shared link.</span>';
      } finally {
        btn.disabled = false;
      }
    }

    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(shareLinkEl.textContent || '');
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1200);
      } catch {
        copyBtn.textContent = 'Failed';
        setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1200);
      }
    });

    btn.addEventListener('click', loadFromAddress);
    addr.addEventListener('keydown', (e) => { if (e.key === 'Enter') loadFromAddress(); });

    const params = new URLSearchParams(window.location.search);
    const lat = params.get('lat');
    const lon = params.get('lon');
    const u = params.get('units') || 'miles';
    if (lat && lon) {
      loadFromShare(lat, lon, u === 'km' ? 'km' : 'miles');
    }
  </script>
</body>
</html>
    """)

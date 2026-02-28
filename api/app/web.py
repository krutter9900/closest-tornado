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
      --card: #101a2f;
      --card-soft: rgba(16, 26, 47, 0.85);
      --text: #e7edf7;
      --muted: #9fb0cc;
      --accent: #5aa5ff;
      --accent-2: #7dd3fc;
      --danger: #ff6b6b;
      --border: rgba(159, 176, 204, 0.22);
      --shadow: 0 14px 38px rgba(0, 0, 0, 0.35);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--text);
      background: radial-gradient(circle at 20% -10%, #1b2b52 0%, #0b1220 45%, #060b16 100%);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
    }

    .shell {
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      gap: 14px;
      padding: 14px;
      min-height: 100vh;
    }

    .card {
      background: var(--card-soft);
      border: 1px solid var(--border);
      border-radius: 16px;
      backdrop-filter: blur(8px);
      box-shadow: var(--shadow);
    }

    .sidebar {
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .title {
      margin: 0;
      font-size: 1.3rem;
      line-height: 1.2;
      letter-spacing: 0.2px;
    }

    .subtitle {
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }

    label {
      color: var(--muted);
      font-size: 0.82rem;
      display: block;
      margin: 0 0 6px;
      letter-spacing: 0.35px;
      text-transform: uppercase;
    }

    .field,
    .select,
    .button {
      width: 100%;
      border-radius: 11px;
      border: 1px solid var(--border);
      font-size: 0.96rem;
    }

    .field,
    .select {
      background: #0f1930;
      color: var(--text);
      padding: 11px 12px;
      outline: none;
      transition: border-color 150ms ease, box-shadow 150ms ease;
    }

    .field:focus,
    .select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(90, 165, 255, 0.15);
    }

    .controls {
      display: grid;
      grid-template-columns: 1fr 120px;
      gap: 8px;
    }

    .button {
      cursor: pointer;
      border: none;
      font-weight: 600;
      color: white;
      padding: 11px 14px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      transition: transform 100ms ease, filter 150ms ease;
    }

    .button:hover { filter: brightness(1.06); }
    .button:active { transform: translateY(1px); }
    .button:disabled { filter: grayscale(0.35) brightness(0.8); cursor: default; }

    .result {
      margin-top: 4px;
      background: rgba(7, 13, 25, 0.72);
      border: 1px solid var(--border);
      border-radius: 13px;
      padding: 12px;
    }

    .stat {
      margin: 0 0 6px;
      font-size: 0.9rem;
      color: var(--muted);
    }

    .value {
      margin: 0 0 10px;
      font-size: 1.35rem;
      font-weight: 700;
      color: #f4f8ff;
    }

    .meta {
      display: grid;
      grid-template-columns: 1fr;
      gap: 5px;
      color: var(--muted);
      font-size: 0.88rem;
    }

    .note-list {
      margin: 10px 0 0;
      padding: 0 0 0 16px;
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.35;
    }

    .error {
      color: var(--danger);
      font-weight: 600;
    }

    .map-wrap {
      position: relative;
      overflow: hidden;
      min-height: calc(100vh - 28px);
    }

    #map {
      position: absolute;
      inset: 0;
    }

    .badge {
      position: absolute;
      right: 14px;
      top: 14px;
      z-index: 4;
      background: rgba(6, 12, 24, 0.8);
      border: 1px solid var(--border);
      border-radius: 999px;
      color: var(--muted);
      font-size: 0.8rem;
      padding: 6px 10px;
      backdrop-filter: blur(6px);
    }

    @media (max-width: 980px) {
      .shell {
        grid-template-columns: 1fr;
        min-height: auto;
      }

      .map-wrap {
        min-height: 62vh;
      }

      .controls {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="card sidebar">
      <div>
        <h1 class="title">Closest Tornado</h1>
        <p class="subtitle">Search any U.S. address to see the nearest historical tornado track and where your closest point lands on it.</p>
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

      <section class="result" id="panel">
        <p class="stat">Ready</p>
        <p class="value">Enter an address</p>
        <div class="meta">Tip: press Enter in the address field to search faster.</div>
      </section>
    </section>

    <section class="card map-wrap">
      <div class="badge">NOAA Storm Events + Geocoding</div>
      <div id="map"></div>
    </section>
  </div>

  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const panel = document.getElementById('panel');
    const addr = document.getElementById('addr');
    const btn = document.getElementById('go');
    const units = document.getElementById('units');

    const map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
      center: [-97.5164, 35.4676],
      zoom: 10
    });
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    function setPanel(html) {
      panel.innerHTML = html;
    }

    function resetLayers() {
      for (const id of ['track', 'closest', 'user']) {
        if (map.getLayer(id)) map.removeLayer(id);
        if (map.getSource(id)) map.removeSource(id);
      }
    }

    async function run() {
      const address = addr.value.trim();
      const selectedUnits = units.value;
      if (!address) return;

      btn.disabled = true;
      btn.textContent = 'Searching…';
      setPanel('<p class="stat">Working</p><p class="value">Looking up location…</p><div class="meta">Checking geocoder + nearest track.</div>');

      try {
        const res = await fetch('/closest-tornado', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ address, units: selectedUnits })
        });

        const data = await res.json();
        if (!res.ok) {
          setPanel(`<p class="stat">Request failed</p><p class="value error">${data.detail || 'Unknown error'}</p><div class="meta">Try a more complete address or retry in a few seconds.</div>`);
          return;
        }

        const q = data.query;
        const r = data.result;

        setPanel(`
          <p class="stat">Closest historical event</p>
          <p class="value">${r.selected_distance.toFixed(3)} ${r.selected_unit}</p>
          <div class="meta">
            <div><strong>Date:</strong> ${r.begin_dt || 'unknown'}</div>
            <div><strong>Scale:</strong> ${r.tor_f_scale || 'unknown'}</div>
            <div><strong>Location:</strong> ${r.cz_name || ''} ${r.state || ''}</div>
            <div><strong>Method:</strong> ${r.distance_type.replaceAll('_', ' ')}</div>
          </div>
          <ul class="note-list">${r.notes.map(n => `<li>${n}</li>`).join('')}</ul>
        `);

        resetLayers();

        map.addSource('track', {
          type: 'geojson',
          data: { type: 'Feature', geometry: r.track_geojson }
        });
        map.addSource('closest', {
          type: 'geojson',
          data: { type: 'Feature', geometry: r.closest_point_geojson }
        });
        map.addSource('user', {
          type: 'geojson',
          data: { type: 'Feature', geometry: { type: 'Point', coordinates: [q.lon, q.lat] }}
        });

        map.addLayer({
          id: 'track',
          type: 'line',
          source: 'track',
          paint: { 'line-width': 4, 'line-color': '#4f9cff' }
        });
        map.addLayer({
          id: 'closest',
          type: 'circle',
          source: 'closest',
          paint: { 'circle-radius': 6, 'circle-color': '#f97316', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }
        });
        map.addLayer({
          id: 'user',
          type: 'circle',
          source: 'user',
          paint: { 'circle-radius': 6, 'circle-color': '#22c55e', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }
        });

        const coords = r.track_geojson.coordinates.slice();
        coords.push([q.lon, q.lat]);
        const bounds = coords.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0]));
        map.fitBounds(bounds, { padding: 72, maxZoom: 14, duration: 700 });
      } catch (err) {
        setPanel('<p class="stat">Unexpected error</p><p class="value error">Could not complete request.</p><div class="meta">Please try again in a moment.</div>');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Find';
      }
    }

    btn.addEventListener('click', run);
    addr.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
  </script>
</body>
</html>
    """)

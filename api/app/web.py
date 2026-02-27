from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Closest Tornado (MVP)</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    body { font-family: Arial, sans-serif; margin: 0; }
    .bar { padding: 12px; display: flex; gap: 8px; align-items: center; border-bottom: 1px solid #ddd; }
    input { flex: 1; padding: 10px; font-size: 14px; }
    button { padding: 10px 14px; }
    #map { height: calc(100vh - 58px); }
    .panel {
      position: absolute; top: 70px; left: 12px; z-index: 2;
      background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ddd;
      max-width: 360px;
    }
    .small { font-size: 12px; color: #444; }
    .err { color: #b00020; }
  </style>
</head>
<body>
  <div class="bar">
    <input id="addr" placeholder="Enter a full address (ex: 123 N Robinson Ave, Oklahoma City, OK 73102)" />
    <button id="go">Find closest tornado</button>
  </div>
  <div id="map"></div>
  <div class="panel" id="panel">
    <div><b>Result</b></div>
    <div class="small">Enter an address and click the button.</div>
  </div>

  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const panel = document.getElementById('panel');
    const addr = document.getElementById('addr');
    const btn = document.getElementById('go');

    // Simple OSM style via MapLibre demo tiles (fine for MVP dev)
    const map = new maplibregl.Map({
      container: 'map',
      style: 'https://demotiles.maplibre.org/style.json',
      center: [-97.5164, 35.4676],
      zoom: 10
    });

    function setPanel(html) { panel.innerHTML = html; }

    async function run() {
      const address = addr.value.trim();
      if (!address) return;

      setPanel('<div><b>Result</b></div><div class="small">Loading...</div>');

      const res = await fetch('/closest-tornado', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ address, units: "miles" })
      });

      const data = await res.json();
      if (!res.ok) {
        setPanel('<div><b>Result</b></div><div class="err">' + (data.detail || 'Error') + '</div>');
        return;
      }

      const q = data.query;
      const r = data.result;

      setPanel(`
        <div><b>Closest tornado</b></div>
        <div class="small"><b>Distance:</b> ${r.distance_miles.toFixed(3)} miles</div>
        <div class="small"><b>Date:</b> ${r.begin_dt || 'unknown'}</div>
        <div class="small"><b>Rating:</b> ${r.tor_f_scale || 'unknown'}</div>
        <div class="small"><b>Location:</b> ${r.cz_name || ''} ${r.state || ''}</div>
        <hr/>
        <div class="small">${r.notes.map(n => '• ' + n).join('<br/>')}</div>
      `);

      // Remove existing layers/sources if present
      for (const id of ['track', 'closest', 'user']) {
        if (map.getLayer(id)) map.removeLayer(id);
        if (map.getSource(id)) map.removeSource(id);
      }

      // Add sources
      map.addSource('track', { type: 'geojson', data: { type: 'Feature', geometry: r.track_geojson }});
      map.addSource('closest', { type: 'geojson', data: { type: 'Feature', geometry: r.closest_point_geojson }});
      map.addSource('user', { type: 'geojson', data: { type: 'Feature', geometry: { type: 'Point', coordinates: [q.lon, q.lat] }}});

      // Track line
      map.addLayer({
        id: 'track',
        type: 'line',
        source: 'track',
        paint: { 'line-width': 4 }
      });

      // Closest point
      map.addLayer({
        id: 'closest',
        type: 'circle',
        source: 'closest',
        paint: { 'circle-radius': 6 }
      });

      // User point
      map.addLayer({
        id: 'user',
        type: 'circle',
        source: 'user',
        paint: { 'circle-radius': 6 }
      });

      // Fit bounds around track + user
      const coords = r.track_geojson.coordinates.slice();
      coords.push([q.lon, q.lat]);
      const bounds = coords.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0]));
      map.fitBounds(bounds, { padding: 60, maxZoom: 14 });
    }

    btn.addEventListener('click', run);
    addr.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
  </script>
</body>
</html>
    """)
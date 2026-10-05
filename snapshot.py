#!/usr/bin/env python3
"""Build dist/launch-window.html: index.html with forecasts for favorites.json embedded.

Published artifacts can't fetch other sites, so the page reads the embedded snapshot instead.
Usage: python3 snapshot.py
"""
import datetime
import json
import math
import os
import re
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).parent
PLACEHOLDER = '<script id="snapshot" type="application/json">null</script>'

# Must match OM_MODELS / OM_SURFACE / OM_LEVEL_VARS / LEVELS in index.html.
MODELS = ['ecmwf_ifs025', 'icon_seamless', 'gfs_seamless']
SURFACE = ['temperature_2m', 'dew_point_2m', 'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m', 'precipitation',
           'precipitation_probability', 'cloud_cover', 'cloud_cover_low', 'cloud_cover_mid', 'cape', 'is_day']
LEVEL_VARS = ['temperature', 'dew_point', 'wind_speed', 'wind_direction', 'geopotential_height']
LEVELS = [1000, 925, 850, 800, 700, 600, 500]
KEEP_HOURS = range(7, 21)  # the page only shows 07:00-20:00 local
SITES_API = 'https://pg.vrana.cz/xcontest/pgmapa.php?locale=en'
NOTE_KEYS = ['limitations', 'air_traffic', 'rules']


def site_from_api(s):
    """Mirrors siteFromApi in index.html."""
    def text(v):
        return (v or '').strip()
    return {
        'name': s['name'], 'lat': s['latitude'], 'lon': s['longitude'], 'alt': s.get('altitude'), 'sup': s.get('superelevation'),
        'wind': [[s['wind_usable_from'], s['wind_usable_to']]] if s.get('wind_usable_from') is not None else s.get('wind_usable'),
        'opt': [[s['wind_optimal_from'], s['wind_optimal_to']]] if s.get('wind_optimal_from') is not None else None,
        'notes': {k: text(s.get(k)) for k in NOTE_KEYS}, 'webcam': (re.findall(r'https?://[^\s,;]+', s.get('link_webcam') or '') or [''])[0], 'url': s.get('url'),
        'closed': s.get('flying_status') == 4 or s.get('active') is False,
    }


def meters(a, b):
    return math.hypot((a['lat'] - b['lat']) * 111e3, (a['lon'] - b['lon']) * 111e3 * math.cos(math.radians(a['lat'])))


def dedupe(items):
    out = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def refresh_site(site, all_sites):
    """Mirrors refreshSite in index.html: launches within 100 m, or same name within 1.5 km, merge into one site."""
    matches = sorted((x for x in all_sites if meters(site, x) < 100 or (x['name'] == site['name'] and meters(site, x) < 1500)),
                     key=lambda x: meters(site, x))
    if not matches:
        print(f"  {site['name']}: not found in Paragliding Mapa, keeping saved data")
        return site
    near, open_ = matches[0], [x for x in matches if not x['closed']]
    use = open_ or matches
    wind = dedupe([w for x in use for w in (x['wind'] or [])])
    opt = dedupe([w for x in use for w in (x['opt'] or [])])
    return {**site, 'alt': near['alt'], 'sup': near['sup'], 'wind': wind or None, 'opt': opt or None,
            'notes': {k: '\n\n'.join(dedupe([x['notes'][k] for x in use if x['notes'][k]])) for k in NOTE_KEYS},
            'webcam': next((x['webcam'] for x in use if x['webcam']), ''), 'url': site.get('url') or near['url'],
            'closed': not open_}


def refresh_sites(sites):
    with urllib.request.urlopen(SITES_API, timeout=120) as r:
        all_sites = [site_from_api(s) for s in json.load(r)['data']]
    print(f'Loaded {len(all_sites)} launches from Paragliding Mapa')
    fresh = []
    for site in sites:
        new = refresh_site(site, all_sites)
        changed = [k for k in ('alt', 'sup', 'wind', 'opt', 'notes', 'closed') if site.get(k) != new.get(k)]
        if changed and 'notes' in site:  # first run only adds the new fields, so stay quiet
            print(f"  {site['name']}: updated {', '.join(changed)}")
        if new['closed']:
            print(f"  WARNING {site['name']} is marked closed/forbidden")
        fresh.append(new)
    return fresh

# Must match WINDY_MODELS / WINDY_LEVELS / WINDY_PARAMS in index.html.
WINDY_MODELS = ['gfs', 'iconEu']
WINDY_LEVELS = ['surface', '850h', '800h', '700h', '600h', '500h']
WINDY_PARAMS = ['wind', 'windGust', 'precip', 'lclouds', 'mclouds', 'hclouds', 'temp', 'dewpoint', 'cape', 'gh']


def windy_key():
    key = os.environ.get('WINDY_KEY')
    path = ROOT / '.windy-key'
    if not key and path.exists():
        key = path.read_text()
    return (key or '').strip() or None


def fetch_windy(site, model, key):
    body = json.dumps({'lat': site['lat'], 'lon': site['lon'], 'model': model, 'parameters': WINDY_PARAMS,
                       'levels': WINDY_LEVELS, 'key': key}).encode()
    req = urllib.request.Request('https://api.windy.com/api/point-forecast/v2', data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    data.pop('units', None)
    return data


def fetch(site):
    hourly = SURFACE + [f'{v}_{p}hPa' for p in LEVELS for v in LEVEL_VARS]
    query = urllib.parse.urlencode({
        'latitude': site['lat'], 'longitude': site['lon'], 'hourly': ','.join(hourly), 'models': ','.join(MODELS),
        'wind_speed_unit': 'ms', 'timezone': 'auto', 'forecast_days': 7,
    })
    for attempt in range(4):
        try:
            with urllib.request.urlopen('https://api.open-meteo.com/v1/forecast?' + query, timeout=60) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            print(f'  Open-Meteo HTTP {e.code}, retrying…', flush=True)
            time.sleep(3 * (attempt + 1))
    h = data['hourly']
    keep = [i for i, t in enumerate(h['time']) if int(t[11:13]) in KEEP_HOURS]
    data['hourly'] = {k: [v[i] for i in keep] for k, v in h.items()}
    data.pop('hourly_units', None)
    return data


def main():
    fav_path = ROOT / 'favorites.json'
    sites = refresh_sites(json.loads(fav_path.read_text()))
    fav_path.write_text('[\n' + ',\n'.join('  ' + json.dumps(s, ensure_ascii=False) for s in sites) + '\n]\n')
    key = windy_key()
    om, windy = {}, {}
    for site in sites:
        print(f"Fetching {site['name']}…", flush=True)
        om[site['key']] = fetch(site)
        if key:
            windy[site['key']] = {}
            for model in WINDY_MODELS:
                try:
                    windy[site['key']][model] = fetch_windy(site, model, key)
                except urllib.error.HTTPError as e:
                    print(f"  Windy {model}: HTTP {e.code} {e.read()[:200]!r}")
        time.sleep(0.3)
    snap = {'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sites': sites, 'om': om}
    if windy:
        snap['windy'] = windy
        warning = next((m.get('warning') for w in windy.values() for m in w.values() if m.get('warning')), None)
        if warning:
            print(f'Windy warning: {warning}')
    payload = json.dumps(snap, separators=(',', ':')).replace('</', '<\\/')
    html = (ROOT / 'index.html').read_text()
    assert PLACEHOLDER in html, 'snapshot placeholder missing from index.html'
    out = ROOT / 'dist' / 'launch-window.html'
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace(PLACEHOLDER, f'<script id="snapshot" type="application/json">{payload}</script>'))
    print(f'Wrote {out} ({out.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()

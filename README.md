# Launch Window

Scores paragliding launches for each of the next 7 days. Each score compares the forecast with the launch's usable wind directions and your pilot profile.

- `index.html` is the live app. Open it in a browser. It fetches forecasts from Open-Meteo (ECMWF, ICON, GFS) and, if you add keys under **Wing, sources & keys**, from Windy and Meteoblue. You can add any of about 14,600 open launches from Paragliding Mapa by name, or by location: type a town, region or `lat, lon` and pick a radius to list nearby launches (place names are looked up with Open-Meteo's geocoding service). This is the same source the Windy plugin `vrana/windy-plugin-pg-mapa` uses: `https://pg.vrana.cz/xcontest/pgmapa.php`.
- `snapshot.py` builds `dist/launch-window.html`. It fetches forecasts for the sites in `favorites.json` and embeds them in the page. Published artifacts can't fetch other sites, so the artifact shows this snapshot. To update it, rerun the script and republish.
- On every build, `snapshot.py` also downloads Paragliding Mapa again and updates each site's altitude, sectors, optimal sectors, notes and closed status in `favorites.json`. Launches within 100 m, or with the same name within 1.5 km, merge into one site, as Shumen's two launches do. The live app does the same each time it opens.
- `favorites.json` lists the sites in the snapshot. In the live app, **Copy list as favorites.json** copies your current site list in this format.

## Scoring

There are two scores, picked with the **Thermal / Soaring** switch next to the pilot profile. The board, best spots, hourly table and factor bars follow the switch; the location details always show both day scores as bars with the flyable threshold (60).

- **Thermal** (10:00 to 18:00): favours light wind and a high thermal top. The thermal top above the launch scores full marks from 1,200 m, with 800 m as the threshold; thick cloud and night hours weaken it. Light wind from any direction is fine.
- **Soaring** (09:00 to 19:00): ridge lift. The wind at the launch must sit between the soaring minimum (3 m/s) and your profile limit, shown as a bar with two red lines. It must blow straight up the slope (cross wind scores 0.35, light wind gets no allowance), and the cloud base needs to be at least 300 m above the launch. Thermals are not scored.

Each hour gets a score from 0 to 100. It's the product of these factors:

- wind speed at the launch
- forward penetration: the strongest forecast wind or surface gust from the ground to 1,000 m above launch, conservatively treated as a headwind, against your estimated loaded trim airspeed. Points drop above 70% of trim and reach zero at or above trim in both flying modes. This does not relax the pilot profile's wind, gust or turbulence limits.
- wind direction against the launch sectors: 1.0 in the optimal sector (`wind_optimal_*`, where the database has it), 0.85 elsewhere in a usable sector, 0.6 within ±22.5° (cross wind), and almost zero outside
- lee side: wind from behind the launch at 300, 600 or 1,000 m above it (rotor)
- gusts: the gust peak (starts costing points at 75% of your profile's limit) and the gust spread above the mean wind (turbulence), whichever is worse
- wind 1,000 m above the launch
- rain amount and probability
- cloud base against launch altitude
- thermal top from a dry-adiabat parcel lifted from the 2 m temperature (thermal score only)
- CAPE (storm risk)

The **Best spots** list ranks site-days scoring 40 or more. On a tie, the calmer gusts rank first. Each board tile has a small windsock for the average wind at the launch in that day's best window, across models. It points downwind like a real sock; each filled stripe is about 1.5 m/s and all four fill from 6 m/s. The speed in m/s is next to it. Best spots show the strongest gust in the best window across all models, amber near your limit and red over it.

Set your **wing class** (EN A–D or CCC) and **all-up flight weight** under **Wing, sources & keys**. All-up weight includes pilot, wing, harness, reserve, clothing, ballast and equipment. For the same wing size, estimated trim speed is `reference trim speed × √(flight weight / reference weight)`. The defaults are EN B and 100 kg flight/reference weight; rough class speed presets are A 36, B 38, C 39, D/CCC 40 km/h. Class alone does not determine performance: replace the preset with your wing's published unaccelerated trim airspeed and the all-up weight it was measured at. These are estimates, not measured groundspeeds or permission to exceed the certified weight range; speed-bar gains are not assumed. Without pressure-level data, penetration aloft is unknown. Saving recalculates all scores, including in published snapshots, without downloading forecasts unless API keys changed.

A model's day score is its best 3-hour stretch between 10:00 and 18:00 local time. The board shows the average across models. The dots show how closely the models agree. The limits for each pilot profile are in `PROFILES` in `index.html`.

The detail panel also shows the site's limitations, airspace and rules notes, plus a webcam link, when Paragliding Mapa has them. Closed or forbidden sites get a warning.

Under the sounding, each factor is drawn as bars of its measured values in their own units (m/s, °, m, %, mm/h, J/kg). A red line marks the threshold: a maximum such as your wind or gust limit, or a minimum such as cloud base 150 m above the launch. Bars are green within limits, amber near the threshold and red past it.

Hover over any element (or focus it with the keyboard) to see a popup explaining what it shows: board tiles list each model's score, the flyable window, model agreement and the main limiting factor; bars explain their measurement and threshold; the sounding has a reading guide.

## Deploy with Docker

The app is a single static page, served by an unprivileged nginx container. There is no backend, database or cookie.

```bash
docker compose up -d --build
```

It listens on port 8080. Set `PORT=9000 docker compose up -d` to use another host port. Put it behind your own reverse proxy (Caddy, Traefik, nginx) for HTTPS.

### Privacy

- Everything a visitor sets up stays in their own browser's local storage: sites, pilot profile, wing settings, model choices, and Windy and Meteoblue API keys. **Wing, sources & keys → Clear my data in this browser** erases it.
- The browser calls the data providers directly (Open-Meteo for forecasts and place search, Paragliding Mapa for launches, Windy and Meteoblue only when the visitor adds a key). Nothing passes through or is stored on your server.
- nginx keeps no access log, logs only critical errors (normal error lines contain client IPs), sets no cookies and refuses anything but GET and HEAD.
- Fonts are bundled in the image, so visitors make no requests to Google.
- Response headers restrict the page to those API hosts (`Content-Security-Policy`), send no referrer, and block framing.
- The container runs as a non-root user with a read-only filesystem, all capabilities dropped and `no-new-privileges`.
- Only `index.html`, `fonts/` and the nginx config are copied into the image (see `.dockerignore`). `.windy-key`, `snapshot.py` and the git history stay out.

Your reverse proxy may keep its own access logs. Turn them off there too if visitor IPs must not be recorded anywhere.

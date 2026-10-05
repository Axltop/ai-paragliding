# Launch Window

Scores paragliding launches for each of the next 7 days. Each score compares the forecast with the launch's usable wind directions and your pilot profile.

- `index.html` is the live app. Open it in a browser. It fetches forecasts from Open-Meteo (ECMWF, ICON, GFS) and, if you add keys under **Sources & keys**, from Windy and Meteoblue. You can add any of about 14,600 open launches from Paragliding Mapa by name, or by location: type a town, region or `lat, lon` and pick a radius to list nearby launches (place names are looked up with Open-Meteo's geocoding service). This is the same source the Windy plugin `vrana/windy-plugin-pg-mapa` uses: `https://pg.vrana.cz/xcontest/pgmapa.php`.
- `snapshot.py` builds `dist/launch-window.html`. It fetches forecasts for the sites in `favorites.json` and embeds them in the page. Published artifacts can't fetch other sites, so the artifact shows this snapshot. To update it, rerun the script and republish.
- On every build, `snapshot.py` also downloads Paragliding Mapa again and updates each site's altitude, sectors, optimal sectors, notes and closed status in `favorites.json`. Launches within 100 m, or with the same name within 1.5 km, merge into one site, as Shumen's two launches do. The live app does the same each time it opens.
- `favorites.json` lists the sites in the snapshot. In the live app, **Copy list as favorites.json** copies your current site list in this format.

## Scoring

Each hour gets a score from 0 to 100. It's the product of these factors:

- wind speed at the launch
- wind direction against the launch sectors: 1.0 in the optimal sector (`wind_optimal_*`, where the database has it), 0.85 elsewhere in a usable sector, 0.6 within ±22.5° (cross wind), and almost zero outside
- lee side: wind from behind the launch at 300, 600 or 1,000 m above it (rotor)
- gusts: the gust peak (starts costing points at 75% of your profile's limit) and the gust spread above the mean wind (turbulence), whichever is worse
- wind 1,000 m above the launch
- rain amount and probability
- cloud base against launch altitude
- thermal top from a dry-adiabat parcel lifted from the 2 m temperature
- CAPE (storm risk)

The **Best spots** list ranks site-days scoring 40 or more. On a tie, the calmer gusts rank first. Each board tile has a small windsock for the average wind at the launch in that day's best window, across models. It points downwind like a real sock; each filled stripe is about 1.5 m/s and all four fill from 6 m/s. The speed in m/s is next to it. Best spots show the strongest gust in the best window across all models, amber near your limit and red over it.

A model's day score is its best 3-hour stretch between 10:00 and 18:00 local time. The board shows the average across models. The dots show how closely the models agree. The limits for each pilot profile are in `PROFILES` in `index.html`.

The detail panel also shows the site's limitations, airspace and rules notes, plus a webcam link, when Paragliding Mapa has them. Closed or forbidden sites get a warning.

Under the sounding, each factor is drawn as bars of its measured values in their own units (m/s, °, m, %, mm/h, J/kg). A red line marks the threshold: a maximum such as your wind or gust limit, or a minimum such as cloud base 150 m above the launch. Bars are green within limits, amber near the threshold and red past it.

Hover over any element (or focus it with the keyboard) to see a popup explaining what it shows: board tiles list each model's score, the flyable window, model agreement and the main limiting factor; bars explain their measurement and threshold; the sounding has a reading guide.

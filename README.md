# Made for the Feed

A data story about Australian content creators, built with Vega-Lite for FIT3179 Data Visualisation 2 (Monash, Semester 2 2026).

**Live page:** https://junng03.github.io/FIT3179-DV2/

## Project structure

```
index.html            the single scrolling page (five acts + about + sources)
css/style.css         layout and typography
js/main.js            loads each spec; shows a "data pending" card if its CSV is missing
specs/*.vl.json       one human-readable Vega-Lite spec per chart (charts 5 and 6 share one, linked)
specs/03_*.vg.json    the zoomable treemap, a full Vega spec (Vega-Lite has no treemap)
data/*.csv            chart data (see checklist below)
scripts/build_creators.py   creators.csv + videos.csv (Wikidata/Wikipedia candidates + YouTube Data API)
scripts/clean_acma.py       ACMA data tables -> charts 1 and 2
archive/              specs, data and scripts from the earlier plan (not used by the page)
sketch/               put sketch.pdf (your hand-drawn A4 sketch) here
```

## Preview locally

The page fetches CSV and JSON files, so it must be served over http (opening `index.html` directly will not work).

- VS Code: install the **Live Server** extension, right-click `index.html`, then choose **Open with Live Server**.
- Or, from the project folder: `python -m http.server 8000` and open http://localhost:8000

## Deploy to GitHub Pages

```bash
git init
git add .
git commit -m "Initial site"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

Then on GitHub: **Settings, Pages, Build and deployment, Source: Deploy from a branch, Branch: main / root**. The repository must be **public**. Check the live URL in a private window before submitting.

## Data checklist

Rule: real, published data only. Never type in an estimate. Raw downloads are not committed; each script's docstring names the source file and URL.

| # | Chart (idiom) | File | Where it comes from | Status |
|---|---|---|---|---|
| 1 | Bump chart (highlight menu; rank / share switch) | `acma_services_by_year.csv` | ACMA data tables QF8, 2020-2025 (`scripts/clean_acma.py`) | **Done** |
| 2 | Dumbbell (sort switch) | `acma_ugc_by_age.csv` | ACMA data tables QF4 by age, 2024 vs 2025 (`scripts/clean_acma.py`) | **Done** |
| 3 | Zoomable treemap (Vega; click to zoom, size switch) | `creators.csv` | `scripts/build_creators.py` (needs `YT_API_KEY`); main category = most-used YouTube category in the 50 latest uploads | **Done** |
| 4 | Strip plot (show length / views / likes, sort switch, creator menu, legend filter) | `videos.csv` | Same; 50 latest uploads per creator, Short = 180 s or less; views and likes added by `scripts/add_video_stats.py` (17 Oct 2026) | **Done** |
| 5-6 | Symbol map + bar chart (linked click, measure switch) | `creators.csv` | Same; cities from `creator_cities.csv` | **Done** (12 of 40 have a sourced city) |
| 7 | Tile grid map (hover links the 4 maps) | `trends_state.csv` + `state_tiles.csv` | `scripts/fetch_trends.py` (Google Trends topics, YouTube Search, AU, 12 months); 0 = too little volume, stored blank | **Done** |
| 8 | World choropleth (all-four average or one creator, Asia-Pacific zoom) | `trends_world.csv` | `scripts/fetch_trends.py` (worldwide); dropdown options in the spec match the 4 creators | **Done** |
| 9 | Waffle chart (age switch) | `kids_youtube_reach.csv` | Roy Morgan (2026): all 6-13, 6-7 and 8-13 | **Done** |
| 10 | Heatmap (row hover) | `kids_age_category.csv` | Roy Morgan (2026): ages 6-9 and 10-13 (top categories only) + all 6-13; unpublished cells left blank | **Done** |
| 11 | Butterfly (sort and difference switches) | `kids_category_by_gender.csv` | Roy Morgan (2026), 12 categories; base = boys/girls 6-13 who watch YouTube | **Done** |
| 12 | Timeline (legend filter) | `timeline_events.csv` | eSafety, ACMA, UC, IAB | **Done** |

## Map boundaries

- **World:** Natural Earth `world-110m.json` from vega-datasets, loaded from the jsDelivr CDN.
- **Australian states:** `rowanhogan/australian-states` GeoJSON, loaded from the jsDelivr CDN. Its licence is not stated. For a cleaner citation and a faster page, consider replacing it with ABS ASGS 2021 State and Territory boundaries (CC BY 4.0), simplified at https://mapshaper.org (aim for under 300 KB). Save it as `data/states.geojson`, update the `url` in spec 05_06, and keep the `STATE_NAME` property (or update the lookup).

## Before submitting

- [x] Replace every `[Your full name]` in `index.html`
- [ ] Every chart renders (no "data pending" cards left)
- [ ] Sources list matches what is actually used; add any new sources
- [ ] `sketch/sketch.pdf` uploaded (hand-drawn; a digital sketch scores 0)
- [ ] AI-use acknowledgement in the footer is accurate
- [ ] Page loads quickly; total data well under a few MB
- [ ] No horizontal scrolling on a small laptop screen
- [ ] Live URL works in a private window

Due Sunday 25 October 2026, 11:55 PM. Interview in the Week 12 studio.

"""Fetch Google Trends search interest for charts 7 and 8.

Settings (same as a manual export from trends.google.com):
  - property: YouTube Search
  - time: past 12 months
  - one creator per query, so each creator is scored 0-100 against their own peak
  - each creator is queried as a Google Trends *topic* (entity), not plain text, so that
    "Lachlan" means the YouTuber Lachlan Power rather than everyone named Lachlan
  - chart 7: geo = Australia, "Interest by subregion" (states and territories)
  - chart 8: worldwide, "Interest by region" (countries)
Google reports places with too little search volume as 0. That is "not enough data", not zero
interest, so those states get a blank interest and a note, and are left out of the world file.

Uses the unofficial pytrends library (pip install pytrends). Google may rate-limit it; if so, export
the same views by hand from trends.google.com and save them in the CSV formats below.

Usage (from the project root): python scripts/fetch_trends.py iso3166.csv
  iso3166.csv: https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes (all/all.csv)
Writes: data/trends_state.csv (creator, state, interest, note, topic_id, fetched)
        data/trends_world.csv (creator, country, iso_n3, interest, topic_id, fetched)
"""
import csv, datetime as dt, os, sys, time
from pytrends.request import TrendReq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Display name -> Google Trends topic id (found with TrendReq.suggestions)
CREATORS = {
    "How Ridiculous": "/g/11gxfrc2js",
    "LazarBeam": "/g/11f0z17w6n",
    "Lachlan": "/g/11j37lbg61",
    "Bridey Drake": "/g/11fnrz_2x0",
}
TIMEFRAME = "today 12-m"
# Google Trends country names that differ from the ISO list
ALIASES = {
    "United States": "United States of America",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "South Korea": "Korea, Republic of", "North Korea": "Korea, Democratic People's Republic of",
    "Russia": "Russian Federation", "Vietnam": "Viet Nam", "Taiwan": "Taiwan, Province of China",
    "Iran": "Iran, Islamic Republic of", "Syria": "Syrian Arab Republic", "Laos": "Lao People's Democratic Republic",
    "Bolivia": "Bolivia, Plurinational State of", "Venezuela": "Venezuela, Bolivarian Republic of",
    "Tanzania": "Tanzania, United Republic of", "Moldova": "Moldova, Republic of", "Czechia": "Czechia",
    "Netherlands": "Netherlands, Kingdom of the", "Turkey": "Türkiye", "Brunei": "Brunei Darussalam",
    "Côte d’Ivoire": "Côte d'Ivoire", "Congo - Kinshasa": "Congo, Democratic Republic of the",
    "Congo - Brazzaville": "Congo", "Myanmar (Burma)": "Myanmar", "Palestine": "Palestine, State of",
    "Hong Kong": "Hong Kong", "Macao": "Macao", "Micronesia": "Micronesia, Federated States of",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina", "Trinidad & Tobago": "Trinidad and Tobago",
    "St. Lucia": "Saint Lucia", "Kosovo": None,
}


def query(py, topic, geo, resolution):
    for attempt in range(5):
        try:
            py.build_payload([topic], timeframe=TIMEFRAME, geo=geo, gprop="youtube")
            return py.interest_by_region(resolution=resolution, inc_low_vol=False, inc_geo_code=False)
        except Exception as e:  # rate limits surface as generic exceptions
            wait = 30 * (attempt + 1)
            print(f"  retry in {wait}s ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)
            time.sleep(wait)
    sys.exit("Google Trends kept refusing. Export these views by hand from trends.google.com instead.")


def main(iso_path):
    with open(iso_path, encoding="utf-8") as f:
        iso = {r["name"]: int(r["country-code"]) for r in csv.DictReader(f)}
    today = dt.date.today().isoformat()
    states, world, unmatched = [], [], set()
    for name, topic in CREATORS.items():
        # A fresh session per query: reusing one session made the worldwide query return Australian states
        df = query(TrendReq(hl="en-AU", tz=-600, timeout=(10, 30)), topic, "AU", "REGION")
        for state, v in df[topic].items():
            low = int(v) == 0
            states.append({"creator": name, "state": state, "interest": "" if low else int(v),
                           "note": "Too little search volume" if low else "", "topic_id": topic, "fetched": today})
        time.sleep(10)
        df = query(TrendReq(hl="en-US", tz=0, timeout=(10, 30)), topic, "", "COUNTRY")
        for country, v in df[topic].items():
            if int(v) == 0:
                continue
            iso_name = ALIASES.get(country, country)
            code = iso.get(iso_name) if iso_name else None
            if code is None:
                unmatched.add(country)
                continue
            world.append({"creator": name, "country": country, "iso_n3": code, "interest": int(v), "topic_id": topic, "fetched": today})
        print(f"{name}: {len(df)} countries returned", file=sys.stderr)
        time.sleep(10)
    if unmatched:
        print(f"No ISO code for (left out): {sorted(unmatched)}", file=sys.stderr)
    for fname, rows in (("trends_state.csv", states), ("trends_world.csv", world)):
        with open(os.path.join(ROOT, "data", fname), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        print(f"data/{fname}: {len(rows)} rows")


if __name__ == "__main__":
    main(sys.argv[1])

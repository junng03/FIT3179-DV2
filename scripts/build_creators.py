"""Build the creator data for charts 3-6 from public sources.

Who counts as a candidate (reproducible, no hand-picking):
  1. Wikidata items with a YouTube channel ID (P2397), linked to Australia (citizenship, country or
     country of origin), whose occupation is YouTuber / vlogger / streamer / influencer / content
     creator / internet celebrity / podcaster.
  2. Articles in Wikipedia's "Australian YouTubers" category tree that have a YouTube channel ID on Wikidata.
  3. The author's starter handles in STARTER.
Then, from the YouTube Data API v3:
  - keep channels whose self-declared country is Australia (snippet.country == "AU"),
  - drop hidden subscriber counts,
  - keep one channel per creator (their biggest),
  - keep the TOP_N creators by subscribers,
  - read each creator's RECENT_N most recent uploads (length, category, made-for-kids flag, views, likes).
A channel's main category is the YouTube category used most often across those uploads (creators
choose the category for each video). A video counts as a Short if it is 180 seconds or shorter,
because the API has no Shorts flag and Shorts can be up to 3 minutes long.
Home city comes only from data/creator_cities.csv, where every city has a quoted source.
City coordinates come from each place's Wikipedia page coordinates.

Usage (from the project root):
    $env:YT_API_KEY = "..."      # PowerShell   (bash: export YT_API_KEY=...)
    python scripts/build_creators.py
Writes: data/creators.csv, data/videos.csv
"""
import csv, datetime as dt, json, os, re, statistics, sys, time
import urllib.error, urllib.parse, urllib.request
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP_N = 40
RECENT_N = 50
SHORT_MAX_S = 180
STARTER = ["brideydrake", "superwog", "norrisnutsdostuff", "isaacbutterfield", "friendlyjordies", "fairbairnfilms"]
UA = {"User-Agent": "FIT3179-student-viz/1.0 (university coursework)"}
OCCUPATION_RE = "youtuber|vlogger|streamer|influencer|content creator|internet celebrity|internet personality|podcaster|social media"
YT = "https://www.googleapis.com/youtube/v3/"


def get_json(url, params, tries=6, headers=UA):
    for t in range(tries):
        try:
            req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=headers)
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504): raise
            time.sleep(8 * (t + 1))
    raise RuntimeError(f"Rate limited: {url}")


def wikidata_pool():
    q = f"""SELECT ?item ?itemLabel ?channel WHERE {{
      ?item wdt:P2397 ?channel ; wdt:P106 ?occ .
      {{ ?item wdt:P27 wd:Q408 }} UNION {{ ?item wdt:P17 wd:Q408 }} UNION {{ ?item wdt:P495 wd:Q408 }}
      ?occ rdfs:label ?ol . FILTER(LANG(?ol) = "en") FILTER(REGEX(?ol, "{OCCUPATION_RE}", "i"))
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
    rows = get_json("https://query.wikidata.org/sparql", {"query": q, "format": "json"})["results"]["bindings"]
    return {r["channel"]["value"]: r["itemLabel"]["value"] for r in rows}


def wikipedia_category_pool():
    api = "https://en.wikipedia.org/w/api.php"
    seen, todo, pages = set(), ["Category:Australian YouTubers"], set()
    while todo:
        cat = todo.pop(); seen.add(cat); cont = {}
        while True:
            r = get_json(api, {"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": 500, "format": "json", **cont})
            for m in r["query"]["categorymembers"]:
                if m["ns"] == 14 and m["title"] not in seen and m["title"] not in todo: todo.append(m["title"])
                elif m["ns"] == 0: pages.add(m["title"])
            time.sleep(1)
            if "continue" not in r: break
            cont = r["continue"]
    titles, qids = sorted(pages), {}
    for i in range(0, len(titles), 50):
        r = get_json(api, {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item", "titles": "|".join(titles[i:i + 50]), "format": "json"})
        qids.update({p["pageprops"]["wikibase_item"]: p["title"] for p in r["query"]["pages"].values() if "pageprops" in p})
        time.sleep(1)
    out, ids = {}, list(qids)
    for i in range(0, len(ids), 50):
        r = get_json("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]), "props": "claims", "format": "json"})
        for q, e in r["entities"].items():
            for c in e.get("claims", {}).get("P2397", []):
                v = c["mainsnak"].get("datavalue", {}).get("value")
                if v: out[v] = qids[q]
        time.sleep(2)
    return out


def youtube(key, endpoint, params):
    return get_json(YT + endpoint, {**params, "key": key}, headers={})


def video_stats(v):
    """Views and likes for one videos.list item. A creator can hide the like count, so a
    missing count is left blank rather than written as 0."""
    st = v.get("statistics", {})
    return {
        "views": int(st["viewCount"]) if "viewCount" in st else "",
        "likes": int(st["likeCount"]) if "likeCount" in st else "",
        "stats_fetched": dt.date.today().isoformat(),
    }


def iso_duration_s(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m: return None
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def place_coords(titles):
    r = get_json("https://en.wikipedia.org/w/api.php", {"action": "query", "prop": "coordinates", "titles": "|".join(titles), "redirects": 1, "format": "json"})
    norm = {n["from"]: n["to"] for n in r["query"].get("normalized", []) + r["query"].get("redirects", [])}
    found = {p["title"]: p["coordinates"][0] for p in r["query"]["pages"].values() if "coordinates" in p}
    return {t: found.get(norm.get(t, t)) for t in titles}


def main():
    key = os.environ.get("YT_API_KEY")
    if not key:
        sys.exit("Set the YT_API_KEY environment variable first.")

    pool = {}  # channel id -> creator name (used to merge a creator's channels)
    pool.update(wikidata_pool())
    pool.update(wikipedia_category_pool())
    for h in STARTER:
        items = youtube(key, "channels", {"part": "id", "forHandle": "@" + h}).get("items", [])
        if items: pool.setdefault(items[0]["id"], "@" + h)
    print(f"candidate channels: {len(pool)}", file=sys.stderr)

    ids, channels = list(pool), []
    for i in range(0, len(ids), 50):
        r = youtube(key, "channels", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50]), "maxResults": 50})
        for it in r.get("items", []):
            s, st = it["snippet"], it["statistics"]
            if s.get("country") != "AU" or st.get("hiddenSubscriberCount"):
                continue
            channels.append({
                "id": it["id"], "channel": s["title"], "handle": s.get("customUrl", ""), "creator": pool[it["id"]],
                "subscribers": int(st.get("subscriberCount", 0)), "views": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0)),
                "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"],
            })
    best = {}
    for c in channels:
        if c["creator"] not in best or c["subscribers"] > best[c["creator"]]["subscribers"]:
            best[c["creator"]] = c
    top = sorted(best.values(), key=lambda c: -c["subscribers"])[:TOP_N]

    cat_names = {c["id"]: c["snippet"]["title"] for c in youtube(key, "videoCategories", {"part": "snippet", "regionCode": "AU"})["items"]}

    video_rows = []
    for c in top:
        items = youtube(key, "playlistItems", {"part": "contentDetails", "playlistId": c["uploads"], "maxResults": RECENT_N}).get("items", [])
        vids = [it["contentDetails"]["videoId"] for it in items]
        vs = youtube(key, "videos", {"part": "snippet,contentDetails,status,statistics", "id": ",".join(vids), "maxResults": 50}).get("items", []) if vids else []
        rows = []
        for v in vs:
            dur = iso_duration_s(v["contentDetails"].get("duration"))
            if dur is None or dur == 0:  # live streams in progress and premieres have no length yet
                continue
            rows.append({
                "channel": c["channel"], "video_id": v["id"], "published": v["snippet"]["publishedAt"][:10],
                "duration_s": dur, "category": cat_names.get(v["snippet"].get("categoryId"), "Unknown"),
                "made_for_kids": bool(v["status"].get("madeForKids")), "is_short": dur <= SHORT_MAX_S,
                **video_stats(v),
            })
        c["n_recent"] = len(rows)
        c["main_category"] = Counter(r["category"] for r in rows).most_common(1)[0][0] if rows else ""
        c["made_for_kids_share"] = round(sum(r["made_for_kids"] for r in rows) / len(rows), 2) if rows else ""
        c["shorts_share"] = round(sum(r["is_short"] for r in rows) / len(rows), 2) if rows else ""
        c["median_duration_s"] = int(statistics.median(r["duration_s"] for r in rows)) if rows else ""
        video_rows += rows

    with open(os.path.join(ROOT, "data", "creator_cities.csv"), encoding="utf-8") as f:
        cities = {r["handle"].lower(): r for r in csv.DictReader(f)}
    coords = place_coords(sorted({r["wiki_place"] for r in cities.values()}))
    missing = [p for p, co in coords.items() if co is None]
    if missing:
        sys.exit(f"No Wikipedia coordinates for: {missing}")

    today, out = dt.date.today().isoformat(), []
    for c in top:
        city = cities.get(c["handle"].lower())
        co = coords[city["wiki_place"]] if city else None
        out.append({
            "channel": c["channel"], "handle": c["handle"], "channel_id": c["id"],
            "category": c["main_category"], "made_for_kids_share": c["made_for_kids_share"],
            "shorts_share": c["shorts_share"], "median_duration_s": c["median_duration_s"], "recent_videos": c["n_recent"],
            "subscribers": c["subscribers"], "views": c["views"], "videos": c["videos"],
            "city": city["city"] if city else "", "lat": round(co["lat"], 4) if co else "", "lon": round(co["lon"], 4) if co else "",
            "city_source": city["source_url"] if city else "", "fetched": today,
        })
    for name, rows in (("creators.csv", out), ("videos.csv", video_rows)):
        with open(os.path.join(ROOT, "data", name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"creators.csv: {len(out)} creators, {sum(1 for o in out if o['city'])} with a sourced city; videos.csv: {len(video_rows)} videos")


if __name__ == "__main__":
    main()

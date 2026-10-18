"""Add view and like counts to the existing data/videos.csv (chart 4).

The videos were collected by build_creators.py on 10 October 2026. This script looks up the same
video IDs again with videos.list (part=statistics, 50 IDs per call) and adds three columns:
views, likes and stats_fetched. Every other column is left exactly as it was, so the other charts
and the text that quote creators.csv / videos.csv do not change.

A creator can hide a video's like count; those likes are left blank, not 0. A video that has been
deleted or made private since 10 October gets blank views and likes.

Usage (from the project root):
    $env:YT_API_KEY = "..."      # PowerShell   (bash: export YT_API_KEY=...)
    python scripts/add_video_stats.py
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_creators import ROOT, video_stats, youtube

PATH = os.path.join(ROOT, "data", "videos.csv")


def main():
    key = os.environ.get("YT_API_KEY")
    if not key:
        sys.exit("Set the YT_API_KEY environment variable first.")
    with open(PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ids = [r["video_id"] for r in rows]
    stats = {}
    for i in range(0, len(ids), 50):
        items = youtube(key, "videos", {"part": "statistics", "id": ",".join(ids[i:i + 50]), "maxResults": 50}).get("items", [])
        stats.update({v["id"]: video_stats(v) for v in items})
    blank = {"views": "", "likes": "", "stats_fetched": ""}
    for r in rows:
        r.update(stats.get(r["video_id"], blank))
    with open(PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} videos: {len(stats)} found, {sum(1 for r in rows if r['likes'] == '')} without a like count")


if __name__ == "__main__":
    main()

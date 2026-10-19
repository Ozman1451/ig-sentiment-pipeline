#!/usr/bin/env python3

import json, pathlib, os

import json, pathlib
from apify_client import ApifyClient
from decimal import Decimal
from time import time

ROOT = pathlib.Path(__file__).parent.parent
TOKEN = (pathlib.Path.home() / ".config/ig-apify/apify.token").read_text().strip()
URLS = [l.strip() for l in (ROOT / "data/raw/selected_posts.txt").read_text().splitlines() if l.strip()]

print(f"Loaded {len(URLS)} target post URLs for comment scraping.")


max_comments = int(os.environ.get("MAX_COMMENTS", 50))

c = ApifyClient(TOKEN)
run = c.actor("apify/instagram-comment-scraper").call(
    run_input={"directUrls": URLS, "resultsLimit": max_comments},
    max_total_charge_usd=Decimal("3.40")
)


items = list(c.dataset(run.default_dataset_id).iterate_items())
out = ROOT / f"data/raw/comments_{int(time())}.json"
out.write_text(json.dumps(items))
cost = max(float(getattr(run, 'usage_total_usd', 0) or 0), len(items)*0.0027)
print(f"comments: {len(items)} items, cost ~${cost:.3f}")
print(f"output: {out}")

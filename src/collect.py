#!/usr/bin/env python3
import sys, json, pathlib
from apify_client import ApifyClient
from decimal import Decimal

ROOT = pathlib.Path(__file__).parent.parent
TOKEN = (pathlib.Path.home() / ".config/ig-apify/apify.token").read_text().strip()
BRANDS = [l.strip() for l in (ROOT / "config/brands.txt").read_text().splitlines() if l.strip()]

c = ApifyClient(TOKEN)
run = c.actor("apify/instagram-scraper").call(
    run_input={"directUrls": BRANDS, "resultsType": "posts", "resultsLimit": 15},
    max_total_charge_usd=Decimal("0.50")
)
items = list(c.dataset(run.default_dataset_id).iterate_items())
out = ROOT / f"data/raw/posts_{int(__import__('time').time())}.json"
out.write_text(json.dumps(items))
print(f"posts: {len(items)} items, cost ~${max(float(getattr(run, 'usage_total_usd', 0) or 0), len(items)*0.0027):.3f}")
print(f"output: {out}")

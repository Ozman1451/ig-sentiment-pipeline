#!/usr/bin/env python3
import json, hashlib, pathlib, pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
SALT = "ig-demo-salt"

items = []
for f in ROOT.glob("data/raw/comments_*.json"):
    items += json.load(open(f))

print(f"Loaded {len(items)} raw comment records.")

records = []
for item in items:
    records.append({
        "comment_id": item.get("id"),
        "text": item.get("text"),
        "username": item.get("ownerUsername", ""),
        "likes": item.get("likeCount", 0),
        "timestamp": item.get("timestamp"),
    })

df = pd.DataFrame(records)
print(f"raw dataframe: {len(df)} rows")

df = df.dropna(subset=["text"])
df = df.drop_duplicates(subset=["comment_id"])
print(f"after comment_id dedup: {len(df)} rows")

df = df.drop_duplicates(subset=["text", "username"])
print(f"after text/username dedup: {len(df)} rows")

df["user_hash"] = df["username"].apply(
    lambda u: hashlib.sha256((u + SALT).encode()).hexdigest()[:16] if u else ""
)
df = df.drop(columns=["username"])

df["flag"] = ""
df.loc[df["text"].str.contains("dm for|giveaway|win|free", case=False, na=False), "flag"] = "spam"
df.loc[df["text"].str.replace(r"[^\w\s]", "", regex=True).str.strip().eq(""), "flag"] = "emoji_only"

out_path = ROOT / "data/clean/comments.parquet"
df.to_parquet(out_path, index=False)
print(f"clean saved: {len(df)} rows -> {out_path}")

# Cast numpy int64 counts to standard python int for json serialization
flag_counts = {str(k): int(v) for k, v in df["flag"].value_counts().items()}

stats = {
    "rows_in": len(items),
    "rows_out": len(df),
    "flag_counts": flag_counts,
}
(ROOT / "reports/clean_stats.json").write_text(json.dumps(stats, indent=2))
print("Stats saved successfully to reports/clean_stats.json")

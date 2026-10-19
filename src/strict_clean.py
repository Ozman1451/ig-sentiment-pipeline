#!/usr/bin/env python3
import pandas as pd, pathlib, re

ROOT = pathlib.Path.cwd()
path = ROOT / "data/clean/comments.parquet"
df = pd.read_parquet(path)
original_len = len(df)

df["text"] = df["text"].astype(str).str.strip()
df = df[df["text"].str.len() >= 2]

# Use standard Python regex to bypass PyArrow engine limitations
def has_valid_chars(text):
    return bool(re.search(r'[a-zA-Z0-9\u0600-\u06FF]', str(text)))

df = df[df["text"].apply(has_valid_chars)]

print(f"Strict clean complete.")
print(f"Dropped {original_len - len(df)} garbage rows. Rows remaining: {len(df)}")
df.to_parquet(path, index=False)

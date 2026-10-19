#!/usr/bin/env python3
import pandas as pd, pathlib, sys
from openai import OpenAI
from tqdm import tqdm

sys.path.insert(0, str(pathlib.Path.cwd() / "src"))
from schema import Tag

ROOT = pathlib.Path.cwd()
df = pd.read_parquet(ROOT / "data/clean/comments.parquet")
c = OpenAI(base_url="http://localhost:8000/v1", api_key="x")
system = (ROOT / "prompts/tagger_system.md").read_text()

print(f"Starting inference tagging on {len(df)} comments...")

tags = []
for i, row in tqdm(df.iterrows(), total=len(df), desc="Tagging"):
    try:
        r = c.chat.completions.create(
            model="m", temperature=0, max_tokens=200,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": row["text"]}],
            response_format={"type": "json_schema", "json_schema": {"name": "tag", "schema": Tag.model_json_schema()}}
        )
        tag = Tag.model_validate_json(r.choices[0].message.content)
        data = tag.model_dump()
        data["comment_id"] = row["comment_id"]
        tags.append(data)
    except Exception as e:
        print(f"\nError on row {i}: {e}")
        continue

tags_df = pd.DataFrame(tags)
out_path = ROOT / "data/tagged/qwen.parquet"
tags_df.to_parquet(out_path, index=False)
print(f"\nTagged: {len(tags_df)}/{len(df)} rows saved to {out_path}")

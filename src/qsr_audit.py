#!/usr/bin/env python3
import pandas as pd, pathlib, random

ROOT = pathlib.Path.cwd()
clean = pd.read_parquet(ROOT / "data/clean/comments.parquet")
tagged = pd.read_parquet(ROOT / "data/tagged/qwen.parquet")

df = clean.merge(tagged, on="comment_id")
random.seed(101) # New seed for QSR run
sample = df.sample(min(60, len(df)))

audit = sample[["comment_id", "text", "sentiment", "aspects"]].copy()
audit["aspect"] = audit["aspects"].apply(lambda x: x[0] if len(x) > 0 else "none")
audit["is_correct"] = ""
audit = audit.drop(columns=["aspects"])

out_path = ROOT / "reports/qsr_audit_sample.csv"
audit.to_csv(out_path, index=False)
print(f"QSR audit sample created: {len(audit)} rows -> {out_path}")

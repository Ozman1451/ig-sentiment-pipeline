#!/usr/bin/env python3
import pandas as pd, pathlib

ROOT = pathlib.Path.cwd()
clean_df = pd.read_parquet(ROOT / "data/clean/comments.parquet")
tagged_df = pd.read_parquet(ROOT / "data/tagged/qwen.parquet")

# Merge text with tags
df = clean_df.merge(tagged_df, on="comment_id")

# Flatten the aspects list into a string for easy CSV reading
df["aspects_str"] = df["aspects"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))

# Save the master dataset
final_csv = ROOT / "reports/final_qsr_data.csv"
df.drop(columns=["aspects"]).to_csv(final_csv, index=False)

# Generate Markdown Summary Report
report = ROOT / "reports/qsr_summary.md"
with open(report, "w") as f:
    f.write("# Gen Z QSR Sentiment Report\n\n")
    f.write(f"**Total Valid Comments:** {len(df)}\n\n")
    
    f.write("## 1. Sentiment Breakdown\n")
    for k, v in df["sentiment"].value_counts().items():
        f.write(f"- {k.title()}: {v} ({(v/len(df))*100:.1f}%)\n")
        
    f.write("\n## 2. Top Aspects Discussed\n")
    aspects = df.explode("aspects")["aspects"].value_counts()
    for k, v in aspects.items():
        f.write(f"- {k}: {v}\n")
        
    f.write("\n## 3. Dominant Emotions\n")
    for k, v in df["emotion"].value_counts().head(5).items():
        f.write(f"- {k.title()}: {v}\n")
        
    f.write("\n## 4. Top Intents\n")
    for k, v in df["intent"].value_counts().head(5).items():
        f.write(f"- {k.title()}: {v}\n")

print(f"Aggregation complete!")
print(f"Master CSV: {final_csv}")
print(f"Summary Report: {report}")

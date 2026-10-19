#!/usr/bin/env python3
import pandas as pd, math, pathlib, sys

ROOT = pathlib.Path.cwd()
csv_path = ROOT / "reports/qsr_audit_sample.csv"
df = pd.read_csv(csv_path)

if df["is_correct"].isna().any():
    print("ERROR: Fill all is_correct values (1 or 0) in reports/qsr_audit_sample.csv first.")
    sys.exit(1)

n = len(df)
k = int(df["is_correct"].sum())
p = k / n
z = 1.96
c = p + z*z/(2*n)
m = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
d = 1 + z*z/n
ci_lower = (c - m) / d
ci_upper = (c + m) / d

print(f"\n--- QSR AUDIT RESULTS ---")
print(f"Sample size: {n}")
print(f"Correct: {k}/{n}")
print(f"Accuracy: {p:.1%} (95% CI: {ci_lower:.1%} to {ci_upper:.1%})")

if p >= 0.80:
    print("STATUS: PASS (>= 80%)")
else:
    print("STATUS: FAIL (< 80%)")

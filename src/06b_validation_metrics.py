"""Step 6b. Precision and recall of the dictionary classification against the blind hand-coded
sample (validation/vacancy_sample_for_hand_coding.csv, columns coder_green_1_0 and coder_domains
filled in by a reviewer who did not see the machine labels). Also summarises the context check.

Writes output/tables/t22_validation_metrics.csv. Runs only when the sample has been coded."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir

def prf(y, yhat):
    tp = int(((y == 1) & (yhat == 1)).sum()); fp = int(((y == 0) & (yhat == 1)).sum()); fn = int(((y == 1) & (yhat == 0)).sum())
    p = tp / (tp + fp) if tp + fp else np.nan; r = tp / (tp + fn) if tp + fn else np.nan
    return p, r, tp, fp, fn

def main():
    c = cfg()
    f = path("validation/vacancy_sample_for_hand_coding.csv")
    s = pd.read_csv(f)
    s = s[s["coder_green_1_0"].notna()]
    if s.empty:
        print("No hand-coded rows yet: fill coder_green_1_0 (and optionally coder_domains, e.g. 'G01;G04') in", f); return
    var = pd.read_parquet(work_dir() / "variables.parquet")
    m = s.merge(var, on="job_id")
    rows = []
    p, r, tp, fp, fn = prf(m["coder_green_1_0"].astype(int), m["green_any"])
    rows.append(("green_any", len(m), tp, fp, fn, round(p, 3), round(r, 3)))
    if m["coder_domains"].notna().any():
        for g in sorted(k for k in var.columns if k.startswith("G0") and len(k) == 3):
            y = m["coder_domains"].fillna("").str.contains(g).astype(int)
            p, r, tp, fp, fn = prf(y, m[g]); rows.append((g, len(m), tp, fp, fn, round(p, 3), round(r, 3)))
    out = pd.DataFrame(rows, columns=["variable", "n_coded", "tp", "fp", "fn", "precision", "recall"])
    out.to_csv(path(c["output"]["tables"]) / "t22_validation_metrics.csv", index=False)
    print(out.to_string(index=False))

if __name__ == "__main__":
    main()

"""Step 3. Match the ILO green dictionary (9 domains) and the ILO skills taxonomy (15 subcategories)
against the lemmatised text of each posting, and derive:
  - one binary indicator and one match count per green domain (G01..G09)
  - one binary indicator and one match count per skills subcategory (S01..S15)
  - green_any: 1 if at least one green domain is matched
  - green_share: green matches / (green matches + skills matches)   [share of green tasks among all
    skills and tasks mentioned, as defined in Delaporte, Escudero and Adamczyk (2025)]
  - green_shade: non-green (share = 0), lighter green (0 < share < mean among green vacancies),
    darker green (share >= that mean)
Also writes the matched terms per posting for validation.
Usage: python src/03_green_and_skills_variables.py [lemmas_file]"""
import sys, collections
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir, load_green, load_skills, Matcher

def main():
    c = cfg()
    lem_file = sys.argv[1] if len(sys.argv) > 1 else "lemmas.parquet"
    lem = pd.read_parquet(work_dir() / lem_file)
    green = Matcher(load_green(), "domain_code", "green", c["text"]["max_ngram"])
    skills = Matcher(load_skills(), "subcategory_code", "skills", c["text"]["max_ngram"])
    gcols, scols = green.groups, skills.groups
    rows, terms_rows = [], []
    for job_id, lemmas in zip(lem["job_id"].values, lem["lemmas"].values):
        lemmas = list(lemmas)
        gh = green.match(lemmas); sh = skills.match(lemmas)
        gc = collections.Counter(g for _, g in gh); sc = collections.Counter(g for _, g in sh)
        n_g, n_s = len(gh), len(sh)
        share = n_g / (n_g + n_s) if (n_g + n_s) else 0.0
        rows.append([job_id, n_g, n_s, share, len(lemmas)] + [gc.get(g, 0) for g in gcols] + [sc.get(s, 0) for s in scols])
        terms_rows.append([job_id, ";".join(sorted({t for t, _ in gh})), ";".join(sorted({t for t, _ in sh}))])
    cols = ["job_id", "n_green_matches", "n_skill_matches", "green_share", "n_tokens"] + [f"n_{g}" for g in gcols] + [f"n_{s}" for s in scols]
    df = pd.DataFrame(rows, columns=cols)
    for g in gcols: df[g] = (df[f"n_{g}"] > 0).astype(int)
    for s in scols: df[s] = (df[f"n_{s}"] > 0).astype(int)
    df["green_any"] = (df["n_green_matches"] > 0).astype(int)
    mean_share = df.loc[df["green_any"] == 1, "green_share"].mean()
    df["green_shade"] = np.select([df["green_share"] == 0, df["green_share"] < mean_share], ["non-green", "lighter green"], "darker green")
    df["green_intensity_per_1000"] = 1000 * df["n_green_matches"] / df["n_tokens"].clip(lower=1)
    out = work_dir() / lem_file.replace("lemmas", "variables")
    df.to_parquet(out, index=False)
    pd.DataFrame(terms_rows, columns=["job_id", "green_terms", "skill_terms"]).to_parquet(work_dir() / lem_file.replace("lemmas", "matched_terms"), index=False)
    # term frequency table (for the context check and the exception list)
    tf = collections.Counter()
    for t in pd.DataFrame(terms_rows)[1]:
        for x in t.split(";"):
            if x: tf[x] += 1
    pd.Series(tf).sort_values(ascending=False).rename_axis("term").reset_index(name="n_postings").to_csv(path(c["output"]["tables"]) / "t01_green_term_frequency.csv", index=False)
    print(f"postings {len(df):,} | green_any {df.green_any.mean():.1%} | mean share among green {mean_share:.3f} | darker {(df.green_shade=='darker green').mean():.1%}")
    print(df[gcols].mean().round(3).to_string())

if __name__ == "__main__":
    main()

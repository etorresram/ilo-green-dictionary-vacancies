"""Step 7. Candidate list of occupation-specific technical skills associated with green vacancies
(ToR Output 1, bullet 4): expressions that are over-represented in green vacancies relative to
non-green vacancies *of the same ISCO-08 sub-major group*, beyond the terms already in the green
dictionary and the skills taxonomy.

Method: for each sub-major group with at least `MIN_GREEN` green vacancies, count 1- to 3-gram
lemma expressions (document frequency), drop expressions in either ILO dictionary and expressions
with fewer than `MIN_DF` green documents, and rank by the log-odds ratio with an informative
Dirichlet prior (Monroe, Colaresi and Quinn 2008), which favours expressions that are both frequent
and distinctive. The output is a table to be reviewed by hand; it is a starting point for a national
green skills taxonomy, not a finished one."""
import sys, collections, math
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir, load_green, load_skills, lemmatise_terms, lemmatise_docs, boilerplate_sentences

MIN_GREEN, MIN_DF, TOP, MIN_N, MAX_N = 150, 15, 20, 2, 3
GENERIC = set("""experience year work team job skill ability require include provide company position candidate
role employee benefit opportunity time employment status apply application equal knowledge strong new support
service customer business management manager develop development responsibility qualification degree education
level pay salary hour day week full part location office insurance health dental vision plan life paid 401k
bonus base range compensation description summary duty perform related task requirement preferred prefer
minimum must able ensure maintain assist responsible high school bachelor master follow well communication
veteran disability protect unsolicited resume hsa vacation match process hiring accept address valid record
with commitment community live embrace diversity depend contact point vary manner policy right reserve program""".split())

def main():
    c = cfg()
    lem = pd.read_parquet(work_dir() / "lemmas.parquet")
    var = pd.read_parquet(work_dir() / "variables.parquet", columns=["job_id", "green_any"])
    occ = pd.read_parquet(work_dir() / "occupations.parquet", columns=["job_id", "isco08_submajor", "isco08_submajor_label"])
    df = lem.merge(var, on="job_id").merge(occ, on="job_id").dropna(subset=["isco08_submajor"])
    known = set(lemmatise_terms(load_green()["term"].tolist())) | set(lemmatise_terms(load_skills()["term"].tolist()))
    # expressions that occur in corporate boilerplate (sentences repeated across >= 20 postings) are
    # excluded: they describe the employer or legal notices, not the tasks of the job
    bp_path = work_dir() / "boilerplate_sentences.parquet"
    if bp_path.exists():
        bsent = pd.read_parquet(bp_path)["sentence"].tolist()
    else:
        post = pd.read_parquet(work_dir() / "postings_clean.parquet", columns=["description"])
        bsent = sorted(boilerplate_sentences(post["description"].fillna(""))[0])
    for l in lemmatise_docs(bsent):
        for k in range(MIN_N, MAX_N + 1):
            for i in range(len(l) - k + 1):
                known.add(tuple(l[i:i + k]))
    print(f"{len(bsent):,} boilerplate sentences; {len(known):,} excluded expressions")
    rows = []
    for (code, label), g in df.groupby(["isco08_submajor", "isco08_submajor_label"]):
        ng = int(g.green_any.sum()); nn = int((g.green_any == 0).sum())
        if ng < MIN_GREEN or nn < MIN_GREEN:
            continue
        cg, cn = collections.Counter(), collections.Counter()
        for lemmas, is_green in zip(g["lemmas"].values, g["green_any"].values):
            l = list(lemmas); grams = set()
            for k in range(MIN_N, MAX_N + 1):
                for i in range(len(l) - k + 1):
                    t = tuple(l[i:i + k])
                    if t in known or any(w in GENERIC or len(w) < 3 or w.isdigit() for w in t):
                        continue
                    grams.add(t)
            (cg if is_green else cn).update(grams)
        alpha = 0.01; Ng, Nn = sum(cg.values()), sum(cn.values()); V = len(set(cg) | set(cn))
        for t, fg in cg.items():
            if fg < MIN_DF:
                continue
            fn = cn.get(t, 0)
            lo = math.log((fg + alpha) / (Ng + alpha * V - fg - alpha)) - math.log((fn + alpha) / (Nn + alpha * V - fn - alpha))
            var_ = 1 / (fg + alpha) + 1 / (fn + alpha)
            rows.append((code, label, ng, " ".join(t), fg, round(fg / ng, 3), round(fn / nn, 3), round(lo / math.sqrt(var_), 2)))
    out = pd.DataFrame(rows, columns=["isco08_submajor", "isco08_submajor_label", "n_green_vacancies", "expression", "green_df", "share_green", "share_non_green", "z_log_odds"])
    out = out.sort_values(["isco08_submajor", "z_log_odds"], ascending=[True, False]).groupby("isco08_submajor").head(TOP)
    out.to_csv(path(c["output"]["tables"]) / "t19_candidate_technical_green_skills_by_isco_submajor.csv", index=False)
    print(out.groupby("isco08_submajor_label")["expression"].apply(lambda s: ", ".join(s.head(8))).to_string())

if __name__ == "__main__":
    main()

"""Step 5b. Boilerplate sensitivity test.

Companies paste the same corporate paragraph into every advert ("we aim for net zero greenhouse gas
emissions by 2030"). Such text describes the employer, not the tasks of the job, and inflates green
matches for large advertisers. The ILO method does not remove it; this script measures how much it
matters so that the choice is explicit. A sentence is treated as boilerplate when the same
normalised sentence (>= 6 words) appears in at least BOILER_MIN distinct postings. Green postings
are re-processed with those sentences removed and the headline indicators are recomputed."""
import re, sys, collections
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir, normalise, lemmatise_docs, load_green, load_skills, Matcher, boilerplate_sentences

BOILER_MIN = 20
SENT = re.compile(r"(?<=[.!?])\s+|\n+")

def main():
    c = cfg()
    post = pd.read_parquet(work_dir() / "postings_clean.parquet", columns=["job_id", "title", "description"])
    var = pd.read_parquet(work_dir() / "variables.parquet", columns=["job_id", "green_any", "green_share", "green_shade", "n_green_matches"])
    # sentence frequency over the whole corpus
    boiler, per_doc = boilerplate_sentences(post["description"].fillna(""), BOILER_MIN)
    sents_by_job = dict(zip(post["job_id"], per_doc))
    freq = collections.Counter(x for ss in per_doc for x in set(ss))
    pd.DataFrame({"sentence": sorted(boiler)}).to_parquet(work_dir() / "boilerplate_sentences.parquet", index=False)
    green_ids = var.loc[var.green_any == 1, "job_id"]
    sub = post[post["job_id"].isin(green_ids)].copy()
    sub["text_nb"] = [t + ". " + " . ".join(x for x in sents_by_job[j] if x not in boiler) for j, t in zip(sub["job_id"], sub["title"].fillna(""))]
    sub["n_boiler_sent"] = [sum(1 for x in sents_by_job[j] if x in boiler) for j in sub["job_id"]]
    lem = list(lemmatise_docs(sub["text_nb"].tolist()))
    green = Matcher(load_green(), "domain_code", "green", c["text"]["max_ngram"]); skills = Matcher(load_skills(), "subcategory_code", "skills", c["text"]["max_ngram"])
    ng = np.array([len(green.match(l)) for l in lem]); ns = np.array([len(skills.match(l)) for l in lem])
    sub["n_green_nb"] = ng; sub["share_nb"] = np.where(ng + ns > 0, ng / np.maximum(ng + ns, 1), 0.0)
    still_green = (ng > 0)
    mean_nb = sub.loc[still_green, "share_nb"].mean()
    n_all = len(var)
    res = pd.DataFrame({
        "indicator": ["green vacancies (share of all)", "darker green vacancies (share of all)", "green postings containing at least one boilerplate sentence", "green postings that stop being green without boilerplate", "boilerplate sentences identified (>= %d postings)" % BOILER_MIN],
        "ilo_method": [round(var.green_any.mean(), 4), round((var.green_shade == "darker green").mean(), 4), "", "", ""],
        "without_boilerplate": [round(still_green.sum() / n_all, 4), round(((sub["share_nb"] >= mean_nb) & still_green).sum() / n_all, 4), round((sub["n_boiler_sent"] > 0).mean(), 4), round((~still_green).mean(), 4), len(boiler)]})
    res.to_csv(path(c["output"]["tables"]) / "t21_boilerplate_sensitivity.csv", index=False)
    pd.Series(sorted(boiler, key=lambda s: -freq[s])[:200]).to_csv(path("validation/boilerplate_sentences_top200.csv"), index=False, header=["sentence"])
    print(res.to_string(index=False))

if __name__ == "__main__":
    main()

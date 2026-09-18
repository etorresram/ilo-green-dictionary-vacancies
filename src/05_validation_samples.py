"""Step 5. Build the two validation files that a human reviewer codes by hand.

(a) validation/context_check_snippets.csv
    For every green term that matches at least `context_terms_min_matches` postings, a random
    sample of 40 occurrences with +/- `context_window` words of context. The reviewer marks each
    snippet as 1 (used in the green sense) or 0. A term is retained if at least
    `precision_threshold` (75%) of its snippets are green, following Delaporte et al. (2025).
(b) validation/vacancy_sample_for_hand_coding.csv
    A stratified random sample (half green, half non-green as classified by the dictionary) of
    full descriptions, without the machine classification shown, for blind coding. Precision and
    recall per domain are computed by src/06_validation_metrics.py once the file is filled in.
"""
import re, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir, load_green, normalise, lemmatise_terms

def main():
    c = cfg(); v = c["validation"]; rng = np.random.default_rng(c["seed"])
    post = pd.read_parquet(work_dir() / "postings_clean.parquet", columns=["job_id", "title", "text"])
    var = pd.read_parquet(work_dir() / "variables.parquet", columns=["job_id", "green_any", "green_share"])
    terms = pd.read_parquet(work_dir() / "matched_terms.parquet")
    freq = pd.read_csv(path(c["output"]["tables"]) / "t01_green_term_frequency.csv")
    cand = freq[freq["n_postings"] >= v["context_terms_min_matches"]]["term"].tolist()
    green = load_green().set_index("term")["domain_code"].to_dict()
    # regex on the normalised surface text: allow simple inflections of the last word
    rows = []
    for term in cand:
        ids = terms.loc[terms["green_terms"].str.contains(rf"(?:^|;){re.escape(term)}(?:;|$)", regex=True), "job_id"].values
        take = rng.choice(ids, size=min(40, len(ids)), replace=False)
        sub = post[post["job_id"].isin(take)]
        pat = re.compile(r"\b" + r"\s+".join(re.escape(w) + r"\w{0,3}" for w in term.split()) + r"\b")
        for jid, title, text in zip(sub["job_id"], sub["title"], sub["text"]):
            t = normalise(text)
            m = pat.search(t)
            if not m:
                continue
            words = t.split(); pos = len(t[:m.start()].split())
            snippet = " ".join(words[max(0, pos - v["context_window"]): pos + len(term.split()) + v["context_window"]])
            rows.append((term, green.get(term, ""), jid, title, snippet, ""))
    out = pd.DataFrame(rows, columns=["term", "domain_code", "job_id", "title", "snippet", "is_green_sense_1_0"])
    path("validation").mkdir(exist_ok=True)
    out.to_csv(path("validation/context_check_snippets.csv"), index=False)
    print(f"context check: {len(cand)} terms, {len(out)} snippets")
    # (b) stratified vacancy sample
    n = v["sample_size"] // 2
    g = var[var.green_any == 1].sample(n, random_state=c["seed"])["job_id"]
    ng = var[var.green_any == 0].sample(n, random_state=c["seed"])["job_id"]
    samp = post[post["job_id"].isin(pd.concat([g, ng]))].sample(frac=1, random_state=c["seed"])
    samp = samp.assign(coder_green_1_0="", coder_domains="", coder_notes="")[["job_id", "title", "text", "coder_green_1_0", "coder_domains", "coder_notes"]]
    samp.to_csv(path("validation/vacancy_sample_for_hand_coding.csv"), index=False)
    print(f"hand-coding sample: {len(samp)} postings")

if __name__ == "__main__":
    main()

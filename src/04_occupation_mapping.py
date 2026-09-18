"""Step 4. Assign an ISCO-08 unit group to each posting from its job title.

Chain (all public sources):
  job title  ->  O*NET-SOC 2019 code   (exact match on O*NET titles and alternate titles, then a
                                        token-sort fuzzy match with a documented threshold and a
                                        head-noun check, then keyword rules in
                                        crosswalks/title_keyword_rules.csv as a lowest-confidence tier; the
                                        token-set scorer was rejected because it returns 100 for any
                                        title that merely contains an O*NET title as a subset)
  O*NET-SOC  ->  SOC 2018              (first seven characters)
  SOC 2018   ->  SOC 2010              (BLS crosswalk; may fan out)
  SOC 2010   ->  ISCO-08               (BLS/SOCPC crosswalk, 2012, updated 2015; many-to-many)

Every posting keeps the full set of admissible ISCO-08 codes. When more than one is admissible the
assignment rule is explicit (the ISCO-08 code reached by the largest number of SOC links, ties
broken by the similarity between the job title and the ISCO-08 unit group title, then by the lowest code) and an alternative assignment (the highest admissible code) is stored so
that descriptive results can be re-run under a different rule. See Torres (2026), 'Lost in
Harmonization', on why this matters."""
import re, sys, collections
import numpy as np, pandas as pd
from rapidfuzz import process, fuzz
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir

FUZZY_CUTOFF = 90
MODIFIERS = r"\b(senior|sr|junior|jr|lead|principal|chief|head|staff|associate|assistant|entry level|experienced|" \
            r"remote|hybrid|onsite|on site|part time|full time|contract|temporary|seasonal|intern|internship|" \
            r"i|ii|iii|iv|v|1|2|3|4|5|level \d|urgently hiring|immediate start|sign on bonus|now hiring)\b"

def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.split(r"\s[-–|/]\s|\(|,|:", s)[0]           # drop location / company / parenthetical tails
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def strip_modifiers(s: str) -> str:
    s = re.sub(MODIFIERS, " ", s)
    return re.sub(r"\s+", " ", s).strip()

def main():
    c = cfg()
    df = pd.read_parquet(work_dir() / "postings_clean.parquet", columns=["job_id", "title"])
    occ = pd.read_csv(path(c["crosswalks"]["onet_titles"]), sep="\t")
    alt = pd.read_csv(path(c["crosswalks"]["onet_alt_titles"]), sep="\t")
    # ---- title index: normalised title -> set of O*NET-SOC codes
    idx = collections.defaultdict(set)
    for code, t in zip(occ["O*NET-SOC Code"], occ["Title"]):
        idx[norm(t)].add(code)
    for code, t, s in zip(alt["O*NET-SOC Code"], alt["Alternate Title"], alt["Short Title"]):
        idx[norm(t)].add(code)
        if isinstance(s, str) and s != "n/a":
            idx[norm(s)].add(code)
    keys = list(idx)
    # keyword fallback rules (lowest-confidence tier), applied in priority order
    rules = pd.read_csv(path("crosswalks/title_keyword_rules.csv"), dtype=str).fillna("").astype({"priority": int}).sort_values("priority", kind="stable")
    # ---- SOC 2018 -> SOC 2010 -> ISCO-08
    x = pd.read_excel(path(c["crosswalks"]["soc2010_to_2018"]))
    soc18_to_10 = collections.defaultdict(set)
    for a, b in zip(x["soc18"].astype(str), x["soc10"].astype(str)):
        soc18_to_10[a[:2] + "-" + a[2:6]].add(b[:2] + "-" + b[2:6])
    y = pd.read_excel(path(c["crosswalks"]["isco08_to_soc2010"]), header=6)
    y["isco"] = y["ISCO-08 Code"].astype(int).astype(str).str.zfill(4)     # leading zeros (armed forces)
    soc10_to_isco = collections.defaultdict(set)
    for s, i in zip(y["2010 SOC Code"].astype(str).str.strip(), y["isco"]):
        soc10_to_isco[s].add(i)
    # ---- match unique titles (exact and fuzzy tiers are cached: they never change unless the
    #      O*NET files change; keyword rules are always re-applied)
    cache_path = work_dir() / "title_match_cache.parquet"
    cache = {}
    if cache_path.exists():
        cc = pd.read_parquet(cache_path)
        cache = {t: (set(c.split(";")) if c else set(), h) for t, c, h in zip(cc["title"], cc["onet_soc"], cc["match_method"])}
    uniq = df["title"].fillna("").unique()
    res = {}; direct = {}
    for t in uniq:
        n = norm(t); how = ""; codes = set()
        if t in cache and not cache[t][1].startswith("keyword"):
            codes, how = cache[t]
        elif n in idx:
            codes, how = idx[n], "exact"
        else:
            n2 = strip_modifiers(n)
            if n2 and n2 in idx:
                codes, how = idx[n2], "exact_stripped"
            elif n2:
                m = process.extractOne(n2, keys, scorer=fuzz.token_sort_ratio, score_cutoff=FUZZY_CUTOFF)
                # accept a fuzzy match only when the head noun (last token) of the job title is
                # present in the matched O*NET title; this removes matches such as
                # "print manager" -> "sports centre manager" that share modifiers but not the role
                if m and n2.split()[-1] in m[0].split():
                    codes, how = idx[m[0]], f"fuzzy_{m[1]:.0f}"
        if not codes and (n2 := strip_modifiers(n)):
            for r in rules.itertuples(index=False):
                if re.search(r.pattern, n2):
                    if isinstance(r.isco08_direct, str) and r.isco08_direct:
                        direct[t] = r.isco08_direct; how = f"keyword_p{r.priority}_isco"
                    elif isinstance(r.onet_soc, str) and r.onet_soc:
                        codes, how = {r.onet_soc}, f"keyword_p{r.priority}"
                    break
        res[t] = (codes, how)
    pd.DataFrame([(t, ";".join(sorted(c)), h) for t, (c, h) in res.items() if h and not h.startswith("keyword")], columns=["title", "onet_soc", "match_method"]).to_parquet(cache_path, index=False)
    # ---- ISCO-08 labels (needed for the tie-break and for output)
    st = pd.read_excel(path(c["crosswalks"]["isco08_structure"]))
    st.columns = ["level", "code", "title"] + list(st.columns[3:])
    # codes are stored as numbers in the spreadsheet: zero-pad to the digit count of each level so
    # that sub-major group "01" (armed forces) is not confused with major group "1" (managers)
    st["code"] = [str(int(cd)).zfill(int(lv)) for cd, lv in zip(st["code"], st["level"])]
    lab = dict(zip(st["code"], st["title"]))
    # ---- propagate through the chain
    out = []
    for t, (codes, how) in res.items():
        soc18 = {cd[:7] for cd in codes}
        soc10 = set().union(*[soc18_to_10.get(s, {s}) for s in soc18]) if soc18 else set()
        links = collections.Counter()
        for s in soc10:
            for i in soc10_to_isco.get(s, ()):
                links[i] += 1
        if t in direct:
            links = collections.Counter({direct[t]: 1})
        if links:
            sim = {i: fuzz.token_sort_ratio(norm(t), norm(lab.get(i, ""))) for i in links}
            best = sorted(links.items(), key=lambda kv: (-kv[1], -sim[kv[0]], kv[0]))[0][0]
            alt_assign = max(links)
        else:
            best = alt_assign = None
        out.append((t, how, ";".join(sorted(codes)), ";".join(sorted(soc10)), best, alt_assign, len(links), ";".join(sorted(links))))
    m = pd.DataFrame(out, columns=["title", "match_method", "onet_soc", "soc2010", "isco08", "isco08_alt", "n_isco_candidates", "isco08_candidates"])
    df = df.merge(m, on="title", how="left")
    # ---- labels
    df["isco08_major"] = df["isco08"].str[:1]
    df["isco08_submajor"] = df["isco08"].str[:2]
    df["isco08_major_label"] = df["isco08_major"].map(lab)
    df["isco08_submajor_label"] = df["isco08_submajor"].map(lab)
    df["isco08_label"] = df["isco08"].map(lab)
    df.to_parquet(work_dir() / "occupations.parquet", index=False)
    cov = pd.DataFrame({
        "metric": ["postings", "matched to O*NET-SOC (exact)", "matched (exact after stripping modifiers)", "matched (fuzzy >= %d, same head noun)" % FUZZY_CUTOFF,
                   "matched (keyword rule, lowest confidence)", "with an ISCO-08 code", "with more than one admissible ISCO-08 code"],
        "n": [len(df), (df.match_method == "exact").sum(), (df.match_method == "exact_stripped").sum(), df.match_method.str.startswith("fuzzy").sum(),
              df.match_method.str.startswith("keyword").sum(), df.isco08.notna().sum(), (df.n_isco_candidates > 1).sum()]})
    cov["share"] = (cov["n"] / len(df)).round(3)
    cov.to_csv(path(c["output"]["tables"]) / "t02_occupation_mapping_coverage.csv", index=False)
    print(cov.to_string(index=False))
    print(df["isco08_major_label"].value_counts().to_string())

if __name__ == "__main__":
    main()

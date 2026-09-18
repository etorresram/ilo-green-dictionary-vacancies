"""Step 1 (JobStreet Malaysia corpus). Same outputs as 01_prepare_data.py: data/work_my/postings_clean.parquet
with job_id, title, description, text, listed_month, annual_wage (MYR), isic_section.
Run with CONFIG=config_my.yaml."""
import hashlib, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir

c = cfg()
df = pd.read_parquet(path(c["data"]["postings_parquet"]))
n0 = len(df)
df = df.rename(columns={"job_title": "title", "descriptions": "description", "company": "company_name", "type": "formatted_work_type"})
key = (df["title"].fillna("") + "|" + df["company_name"].fillna("") + "|" + df["description"].fillna(""))
df = df.assign(dup_key=key.map(lambda s: hashlib.md5(s.encode()).hexdigest())).drop_duplicates("dup_key").drop(columns="dup_key")
df = df[df["description"].fillna("").str.len() >= 50]
n1 = len(df)
t = pd.to_datetime(df["listingDate"], errors="coerce", utc=True)
df["listed_date"] = t.dt.date; df["listed_month"] = t.dt.strftime("%Y-%m")
# posted wage: "RM 3,000 – RM 4,500 per month" -> midpoint, annualised in MYR
def parse(s):
    if not isinstance(s, str): return np.nan
    nums = [float(x.replace(",", "")) for x in re.findall(r"RM\s*([\d,]+(?:\.\d+)?)", s.replace("\xa0", " "))]
    if not nums: return np.nan
    v = sum(nums) / len(nums)
    if "hour" in s: return v * c["salary"]["hours_per_year"]
    if "year" in s or "annum" in s: return v
    if "week" in s: return v * c["salary"]["weeks_per_year"]
    return v * 12                                    # per month (the JobStreet default)
df["annual_wage_usd"] = df["salary"].map(parse)       # column name kept for pipeline compatibility; unit is MYR
df.loc[(df["annual_wage_usd"] < c["salary"]["min_annual"]) | (df["annual_wage_usd"] > c["salary"]["max_annual"]), "annual_wage_usd"] = np.nan
imap = pd.read_csv(path(c["dictionaries"]["industry_map"]))
df = df.merge(imap[["category", "isic_section", "isic_section_label"]], on="category", how="left")
df["industry_name"] = df["category"]
df["remote_allowed"] = np.nan; df["formatted_experience_level"] = np.nan
df["text"] = df["title"].fillna("") + ". " + df["description"].fillna("")
df.to_parquet(work_dir() / "postings_clean.parquet", index=False)
path(c["output"]["tables"]).mkdir(parents=True, exist_ok=True)
log = pd.DataFrame({"step": ["raw rows", "after duplicate and empty-text removal", "with posted wage", "with ISIC section"],
                    "n": [n0, n1, int(df["annual_wage_usd"].notna().sum()), int(df["isic_section"].notna().sum())]})
log.to_csv(path(c["output"]["tables"]) / "t00_sample_construction.csv", index=False); print(log.to_string(index=False))
print(df["listed_month"].value_counts().sort_index().to_string())

"""Step 1. Load the raw postings, remove duplicates, annualise posted salaries and attach an
ISIC Rev. 4 section. Writes data/work/postings_clean.parquet (never committed)."""
import hashlib, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir

c = cfg()
cols = ["job_id", "company_name", "title", "description", "max_salary", "med_salary", "min_salary",
        "pay_period", "formatted_work_type", "location", "original_listed_time", "remote_allowed",
        "formatted_experience_level", "skills_desc", "currency", "compensation_type"]
df = pd.read_csv(path(c["data"]["postings_csv"]), usecols=cols)
n0 = len(df)

# --- duplicates: identical title + company + description text
key = (df["title"].fillna("") + "|" + df["company_name"].fillna("") + "|" + df["description"].fillna(""))
df["dup_key"] = key.map(lambda s: hashlib.md5(s.encode()).hexdigest())
df = df.drop_duplicates("dup_key").drop(columns="dup_key")
df = df[df["description"].fillna("").str.len() >= 50]           # empty or truncated ads
n1 = len(df)

# --- dates
df["listed_date"] = pd.to_datetime(df["original_listed_time"], unit="ms").dt.date
df["listed_month"] = pd.to_datetime(df["original_listed_time"], unit="ms").dt.to_period("M").astype(str)

# --- posted wage: annualised USD, using the midpoint of min/max when no median is given
sal = df["med_salary"].copy()
mid = df[["min_salary", "max_salary"]].mean(axis=1)
sal = sal.fillna(mid)
factor = df["pay_period"].map({"YEARLY": 1, "MONTHLY": 12, "WEEKLY": c["salary"]["weeks_per_year"],
                               "BIWEEKLY": 26, "HOURLY": c["salary"]["hours_per_year"]})
df["annual_wage_usd"] = np.where(df["currency"].fillna("USD").eq("USD"), sal * factor, np.nan)
# implausible values (data-entry errors) are set to missing rather than trimmed silently
df.loc[(df["annual_wage_usd"] < 10_000) | (df["annual_wage_usd"] > 1_000_000), "annual_wage_usd"] = np.nan

# --- industry: first LinkedIn industry per job, then ISIC Rev. 4 section
ji = pd.read_csv(path(c["data"]["job_industries_csv"])).drop_duplicates("job_id")
ind = pd.read_csv(path(c["data"]["industries_csv"]))
imap = pd.read_csv(path(c["dictionaries"]["industry_map"]))
ji = ji.merge(ind, on="industry_id", how="left").merge(imap, on="industry_name", how="left")
df = df.merge(ji[["job_id", "industry_name", "isic_section", "isic_section_label"]], on="job_id", how="left")

df["text"] = df["title"].fillna("") + ". " + df["description"].fillna("")
df.to_parquet(work_dir() / "postings_clean.parquet", index=False)

log = pd.DataFrame({"step": ["raw rows", "after duplicate and empty-text removal", "with posted wage",
                             "with ISIC section"],
                    "n": [n0, n1, int(df["annual_wage_usd"].notna().sum()), int(df["isic_section"].notna().sum())]})
log.to_csv(path(c["output"]["tables"]) / "t00_sample_construction.csv", index=False)
print(log.to_string(index=False))

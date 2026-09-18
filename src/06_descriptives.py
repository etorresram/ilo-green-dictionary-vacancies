"""Step 6. Descriptive statistics requested in the ToR that this dataset supports, as CSV tables
(output/tables) and figures (output/figures, PNG via matplotlib and HTML via Plotly).

Items that need a time dimension or applicants' profiles are not produced here: the corpus is a
one-month snapshot of vacancies only. Functions are written by group so that a monthly variable
can be added as an extra grouping key when a time series is available."""
import sys, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.express as px, plotly.graph_objects as go
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path, work_dir, load_green, load_skills

GREEN = "#2E7D32"; GREY = "#9E9E9E"; DARK = "#1B5E20"; LIGHT = "#81C784"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})

def savefig(fig_mpl, fig_plotly, name, T, F):
    fig_mpl.tight_layout(); fig_mpl.savefig(F / f"{name}.png"); plt.close(fig_mpl)
    fig_plotly.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=50, b=40), font=dict(size=12))
    fig_plotly.write_html(F / f"{name}.html", include_plotlyjs="cdn", full_html=False)

def main():
    c = cfg(); T = path(c["output"]["tables"]); F = path(c["output"]["figures"]); T.mkdir(parents=True, exist_ok=True); F.mkdir(parents=True, exist_ok=True)
    post = pd.read_parquet(work_dir() / "postings_clean.parquet", columns=["job_id", "annual_wage_usd", "isic_section", "isic_section_label", "formatted_experience_level", "remote_allowed", "formatted_work_type"])
    var = pd.read_parquet(work_dir() / "variables.parquet")
    occ = pd.read_parquet(work_dir() / "occupations.parquet")
    df = post.merge(var, on="job_id").merge(occ.drop(columns=["title"]), on="job_id", how="left")
    gdom = load_green().drop_duplicates("domain_code").set_index("domain_code")["domain"].to_dict()
    sk = load_skills().drop_duplicates("subcategory_code").set_index("subcategory_code")[["category", "subcategory"]]
    gcols = sorted(gdom); scols = sorted(sk.index)
    summary = {}

    # ---- 1. headline: green share and shade
    t = df["green_shade"].value_counts().reindex(["non-green", "lighter green", "darker green"]).rename_axis("shade").reset_index(name="n")
    t["share"] = (t["n"] / t["n"].sum()).round(4); t.to_csv(T / "t10_green_shade_overall.csv", index=False)
    summary["n_postings"] = int(len(df)); summary["green_share"] = float(df["green_any"].mean()); summary["darker_share"] = float((df["green_shade"] == "darker green").mean())
    summary["mean_green_share_among_green"] = float(df.loc[df.green_any == 1, "green_share"].mean())

    # ---- 2. by ISCO-08 major group (main and alternative assignment)
    def by_group(col, label_col, name, min_n=100):
        g = df.dropna(subset=[col]).groupby([col, label_col]).agg(n=("job_id", "size"), green_share=("green_any", "mean"), darker_share=("green_shade", lambda s: (s == "darker green").mean()), mean_intensity=("green_intensity_per_1000", "mean")).reset_index()
        g = g[g["n"] >= min_n].sort_values("green_share", ascending=False); g[["green_share", "darker_share"]] = g[["green_share", "darker_share"]].round(4)
        g.to_csv(T / f"{name}.csv", index=False); return g
    occ_major = by_group("isco08_major", "isco08_major_label", "t11_green_by_isco_major", 50)
    occ_sub = by_group("isco08_submajor", "isco08_submajor_label", "t12_green_by_isco_submajor", 100)
    ind = by_group("isic_section", "isic_section_label", "t13_green_by_isic_section", 100)
    # alternative ISCO assignment (sensitivity)
    alt = df.dropna(subset=["isco08_alt"]).assign(m=lambda d: d["isco08_alt"].str[:1]).groupby("m")["green_any"].mean().rename("green_share_alt_rule")
    occ_major.merge(alt, left_on="isco08_major", right_index=True, how="left").assign(abs_diff_pp=lambda d: (100 * (d.green_share - d.green_share_alt_rule)).abs().round(2)).to_csv(T / "t11b_green_by_isco_major_sensitivity.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 4)); d = occ_major.sort_values("green_share")
    ax.barh(d["isco08_major_label"], 100 * d["green_share"], color=GREEN); ax.set_xlabel("Share of vacancies with at least one green task (%)"); ax.set_title("Green vacancies by ISCO-08 major group")
    for y, (v, n) in enumerate(zip(d["green_share"], d["n"])): ax.text(100 * v + 0.3, y, f"{100*v:.1f}%  (n={n:,})", va="center", fontsize=7)
    pf = px.bar(d, x=d["green_share"] * 100, y="isco08_major_label", orientation="h", hover_data={"n": True}, labels={"x": "Share of green vacancies (%)", "isco08_major_label": ""}, title="Green vacancies by ISCO-08 major group", color_discrete_sequence=[GREEN])
    savefig(fig, pf, "f01_green_by_isco_major", T, F)

    fig, ax = plt.subplots(figsize=(7, 5)); d = ind.sort_values("green_share")
    ax.barh(d["isic_section_label"].str.slice(0, 45), 100 * d["green_share"], color=GREEN); ax.set_xlabel("Share of green vacancies (%)"); ax.set_title("Green vacancies by ISIC Rev. 4 section")
    pf = px.bar(d, x=d["green_share"] * 100, y="isic_section_label", orientation="h", hover_data={"n": True}, labels={"x": "Share of green vacancies (%)", "isic_section_label": ""}, title="Green vacancies by ISIC Rev. 4 section", color_discrete_sequence=[GREEN])
    savefig(fig, pf, "f02_green_by_isic_section", T, F)

    # ---- 3. sustainability domains among green vacancies
    dom = pd.DataFrame({"domain_code": gcols, "domain": [gdom[g] for g in gcols], "share_of_green_vacancies": [df.loc[df.green_any == 1, g].mean() for g in gcols], "share_of_all_vacancies": [df[g].mean() for g in gcols]}).sort_values("share_of_green_vacancies", ascending=False)
    dom.round(4).to_csv(T / "t14_domains.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 3.8)); d = dom.sort_values("share_of_green_vacancies")
    ax.barh(d["domain"], 100 * d["share_of_green_vacancies"], color=GREEN); ax.set_xlabel("Share of green vacancies mentioning the domain (%)"); ax.set_title("Sustainability domains (ILO Green Dictionary)")
    pf = px.bar(d, x=d["share_of_green_vacancies"] * 100, y="domain", orientation="h", labels={"x": "Share of green vacancies (%)", "domain": ""}, title="Sustainability domains mentioned in green vacancies", color_discrete_sequence=[GREEN])
    savefig(fig, pf, "f03_domains", T, F)

    # ---- 4. skills: green vs non-green (15 subcategories)
    rows = []
    for s in scols:
        rows.append((s, sk.loc[s, "category"], sk.loc[s, "subcategory"], df.loc[df.green_any == 1, s].mean(), df.loc[df.green_any == 0, s].mean(), df.loc[df.green_shade == "darker green", s].mean()))
    skt = pd.DataFrame(rows, columns=["code", "category", "subcategory", "green", "non_green", "darker_green"]); skt["diff_pp"] = 100 * (skt.green - skt.non_green)
    skt.round(4).to_csv(T / "t15_skills_green_vs_nongreen.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.5, 5)); d = skt.iloc[::-1]; y = np.arange(len(d))
    ax.barh(y - 0.2, 100 * d.non_green, 0.4, color=GREY, label="Non-green"); ax.barh(y + 0.2, 100 * d.green, 0.4, color=GREEN, label="Green")
    ax.set_yticks(y); ax.set_yticklabels(d.subcategory, fontsize=7.5); ax.set_xlabel("Share of vacancies mentioning the skill (%)"); ax.legend(); ax.set_title("Skills requirements in green vs non-green vacancies (partial ILO taxonomy)")
    pf = go.Figure([go.Bar(y=d.subcategory, x=100 * d.non_green, orientation="h", name="Non-green", marker_color=GREY), go.Bar(y=d.subcategory, x=100 * d.green, orientation="h", name="Green", marker_color=GREEN)]); pf.update_layout(barmode="group", title="Skills requirements in green vs non-green vacancies", xaxis_title="Share of vacancies (%)", height=550)
    savefig(fig, pf, "f04_skills_green_vs_nongreen", T, F)

    # ---- 5. posted wages
    w = df.dropna(subset=["annual_wage_usd"])
    def wstats(g):
        return pd.Series({"n": len(g), "median_wage": g["annual_wage_usd"].median(), "mean_wage": g["annual_wage_usd"].mean(), "p25": g["annual_wage_usd"].quantile(.25), "p75": g["annual_wage_usd"].quantile(.75)})
    wt = w.groupby("green_shade")[["annual_wage_usd"]].apply(wstats).reindex(["non-green", "lighter green", "darker green"]).round(0); wt.to_csv(T / "t16_wages_by_shade.csv")
    wo = w.groupby(["isco08_major", "isco08_major_label", "green_any"])[["annual_wage_usd"]].apply(wstats).reset_index(); wo = wo[wo.n >= 30]
    wo["green_any"] = wo["green_any"].map({0: "non_green", 1: "green"}); wp = wo.pivot_table(index=["isco08_major", "isco08_major_label"], columns="green_any", values=["median_wage", "n"]).round(0)
    wp.columns = [f"{a}_{b}" for a, b in wp.columns]; wp["premium_pct"] = (100 * (wp["median_wage_green"] / wp["median_wage_non_green"] - 1)).round(1); wp.to_csv(T / "t17_wages_by_isco_major.csv")
    summary["median_wage_green"] = float(w.loc[w.green_any == 1, "annual_wage_usd"].median()); summary["median_wage_nongreen"] = float(w.loc[w.green_any == 0, "annual_wage_usd"].median()); summary["n_with_wage"] = int(len(w))
    d = wp.dropna(subset=["median_wage_green", "median_wage_non_green"]).reset_index()
    fig, ax = plt.subplots(figsize=(7, 4)); y = np.arange(len(d))
    ax.barh(y - 0.2, d.median_wage_non_green / 1000, 0.4, color=GREY, label="Non-green"); ax.barh(y + 0.2, d.median_wage_green / 1000, 0.4, color=GREEN, label="Green")
    ax.set_yticks(y); ax.set_yticklabels(d.isco08_major_label, fontsize=7.5); ax.set_xlabel("Median posted annual wage (thousand USD)"); ax.legend(); ax.set_title("Posted wages, green vs non-green vacancies, by ISCO-08 major group")
    pf = go.Figure([go.Bar(y=d.isco08_major_label, x=d.median_wage_non_green, orientation="h", name="Non-green", marker_color=GREY), go.Bar(y=d.isco08_major_label, x=d.median_wage_green, orientation="h", name="Green", marker_color=GREEN)]); pf.update_layout(barmode="group", title="Median posted annual wage (USD) by ISCO-08 major group", xaxis_title="USD")
    savefig(fig, pf, "f05_wages_by_isco_major", T, F)

    # ---- 6. other characteristics available in the data
    oth = []
    for col in ["formatted_experience_level", "formatted_work_type", "remote_allowed"]:
        g = df.groupby(df[col].fillna("not stated"))["green_any"].agg(["size", "mean"]).reset_index(); g.columns = ["value", "n", "green_share"]; g["characteristic"] = col; oth.append(g)
    pd.concat(oth)[["characteristic", "value", "n", "green_share"]].round(4).to_csv(T / "t18_other_characteristics.csv", index=False)

    # ---- 7. intensity distribution
    fig, ax = plt.subplots(figsize=(6, 3.5)); g = df[df.green_any == 1]
    ax.hist(g["green_share"], bins=40, color=GREEN); ax.axvline(summary["mean_green_share_among_green"], color="black", ls="--", label="mean (lighter / darker cut-off)"); ax.set_xlabel("Share of green tasks among all matched skills and tasks"); ax.set_ylabel("Green vacancies"); ax.legend(); ax.set_title("Green task intensity among green vacancies")
    pf = px.histogram(g, x="green_share", nbins=40, title="Green task intensity among green vacancies", labels={"green_share": "Share of green tasks"}, color_discrete_sequence=[GREEN]); pf.add_vline(x=summary["mean_green_share_among_green"], line_dash="dash")
    savefig(fig, pf, "f06_intensity", T, F)

    json.dump(summary, open(T / "summary.json", "w"), indent=2)
    print(json.dumps(summary, indent=2)); print(occ_major.to_string(index=False))

if __name__ == "__main__":
    main()

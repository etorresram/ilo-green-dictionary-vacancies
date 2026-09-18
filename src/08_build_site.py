"""Step 8. Assemble the static results page (docs/index.html) from the tables and Plotly figures
produced in step 6. No server, no build tools: GitHub Pages serves the folder as is."""
import sys, json, html
import pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, path

def table_html(df, cols=None, n=None):
    d = df if cols is None else df[cols]
    if n: d = d.head(n)
    return d.to_html(index=False, classes="tbl", border=0, float_format=lambda x: f"{x:,.3f}" if abs(x) < 1 else f"{x:,.0f}")

def main():
    c = cfg(); T = path(c["output"]["tables"]); F = path(c["output"]["figures"]); D = path(c["output"]["site"]); D.mkdir(exist_ok=True)
    s = json.load(open(T / "summary.json"))
    fig = {n: open(F / f"{n}.html").read() for n in ["f01_green_by_isco_major", "f02_green_by_isic_section", "f03_domains", "f04_skills_green_vs_nongreen", "f05_wages_by_isco_major", "f06_intensity"]}
    t0 = pd.read_csv(T / "t00_sample_construction.csv"); t2 = pd.read_csv(T / "t02_occupation_mapping_coverage.csv")
    t10 = pd.read_csv(T / "t10_green_shade_overall.csv"); t14 = pd.read_csv(T / "t14_domains.csv"); t16 = pd.read_csv(T / "t16_wages_by_shade.csv")
    t11b = pd.read_csv(T / "t11b_green_by_isco_major_sensitivity.csv"); t19 = pd.read_csv(T / "t19_candidate_technical_green_skills_by_isco_submajor.csv")
    tv = pd.read_csv(T / "t20_context_check_results.csv") if (T / "t20_context_check_results.csv").exists() else None
    tb = pd.read_csv(T / "t21_boilerplate_sensitivity.csv") if (T / "t21_boilerplate_sensitivity.csv").exists() else None
    t19s = t19.groupby("isco08_submajor_label")["expression"].apply(lambda x: ", ".join(x.head(10))).reset_index().rename(columns={"isco08_submajor_label": "ISCO-08 sub-major group", "expression": "Top candidate expressions (over-represented in green vacancies)"})
    css = """
    body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:1000px;margin:0 auto;padding:24px;color:#222;line-height:1.5}
    h1{font-size:1.7rem;margin-bottom:.2rem} h2{font-size:1.25rem;border-bottom:2px solid #2E7D32;padding-bottom:4px;margin-top:2.2rem}
    .sub{color:#555} .kpis{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0} .kpi{flex:1 1 180px;background:#f2f7f2;border-left:4px solid #2E7D32;padding:10px 14px;border-radius:4px}
    .kpi b{font-size:1.5rem;display:block} .tbl{border-collapse:collapse;font-size:.85rem;margin:10px 0;width:100%} .tbl th{background:#e8f0e8;text-align:left;padding:5px 8px} .tbl td{padding:4px 8px;border-bottom:1px solid #e5e5e5}
    .note{background:#fff8e1;border-left:4px solid #f9a825;padding:8px 12px;font-size:.9rem} .fig{margin:12px 0 28px} code{background:#f3f3f3;padding:1px 4px;border-radius:3px} footer{margin-top:40px;font-size:.85rem;color:#666}
    """
    kp = f"""
    <div class="kpis">
      <div class="kpi"><span>Vacancies analysed</span><b>{s['n_postings']:,}</b></div>
      <div class="kpi"><span>Green vacancies (at least one green task)</span><b>{100*s['green_share']:.1f}%</b></div>
      <div class="kpi"><span>Darker green (share of green tasks above the mean)</span><b>{100*s['darker_share']:.1f}%</b></div>
      <div class="kpi"><span>Median posted wage, green vs non-green</span><b>${s['median_wage_green']:,.0f} vs ${s['median_wage_nongreen']:,.0f}</b></div>
    </div>"""
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ILO Green Dictionary applied to online vacancies</title><style>{css}</style></head><body>
    <h1>Measuring green jobs in online vacancies with the ILO Green Dictionary</h1>
    <p class="sub">A documented replication of the ILO methodology (Delaporte, Escudero and Adamczyk 2025; Adamczyk et al. 2025) on a public corpus of {s['n_postings']:,} English-language job postings (LinkedIn, United States, 2024). Code, dictionaries and this page: <a href="https://github.com/etorresram/ilo-green-dictionary-vacancies">github.com/etorresram/ilo-green-dictionary-vacancies</a>. Author: Eric Torres Ramírez.</p>
    {kp}
    <p class="note"><b>Read this first.</b> The corpus is a one-month snapshot of vacancies from one country and one platform, so it cannot show trends over time or compare demand with applicants' profiles. The skills variables use the <em>selected</em> keywords published in the ILO brief, not the full taxonomy. All figures are illustrations of the workflow, not estimates of the US labour market.</p>
    <h2>1. What was done</h2>
    <ol>
      <li><b>Data preparation.</b> Duplicate and empty postings removed; posted salaries annualised; LinkedIn industries mapped to ISIC Rev. 4 sections.</li>
      <li><b>Text pre-processing</b> in the ILO sequence: tokenisation, normalisation, stop-word removal (keeping stop words inside dictionary expressions), lemmatisation (spaCy). Dictionary expressions go through the same pipeline, so matching is lemma-to-lemma on full words.</li>
      <li><b>Green task variables</b>: 9 sustainability domains, binary and counts; a vacancy is green if it matches at least one domain.</li>
      <li><b>Skills variables</b>: 15 subcategories (cognitive, socio-emotional, manual).</li>
      <li><b>Green share and shade</b>: share of green tasks among all matched skills and tasks; non-green (0), lighter green (below the mean among green vacancies), darker green (at or above).</li>
      <li><b>Occupation coding</b>: job title → O*NET-SOC → SOC 2010 → ISCO-08 through official crosswalks, with every admissible code kept and an explicit assignment rule.</li>
      <li><b>Validation</b>: context check of frequent terms (75% rule), a blind hand-coding sample, and a boilerplate sensitivity test.</li>
    </ol>
    {table_html(t0)}
    <h2>2. Green vacancies by occupation and industry</h2>
    <div class="fig">{fig['f01_green_by_isco_major']}</div>
    <p>Occupation coding coverage and ambiguity:</p>{table_html(t2)}
    <p>Sensitivity of the occupational profile to the assignment rule for titles with more than one admissible ISCO-08 code (main rule vs alternative rule):</p>
    {table_html(t11b, ["isco08_major_label", "n", "green_share", "green_share_alt_rule", "abs_diff_pp"])}
    <div class="fig">{fig['f02_green_by_isic_section']}</div>
    <h2>3. Shade of green and sustainability domains</h2>
    {table_html(t10)}
    <div class="fig">{fig['f06_intensity']}</div>
    <div class="fig">{fig['f03_domains']}</div>
    <h2>4. Skills requirements in green versus non-green vacancies</h2>
    <div class="fig">{fig['f04_skills_green_vs_nongreen']}</div>
    <h2>5. Posted wages</h2>
    <p>Posted annual wages (USD, {s['n_with_wage']:,} vacancies with a salary field). No deflation is needed for a one-month snapshot; the code applies a CPI deflator when several months are present.</p>
    {table_html(t16)}
    <div class="fig">{fig['f05_wages_by_isco_major']}</div>
    <h2>6. Candidate occupation-specific technical green skills</h2>
    <p>Expressions over-represented in green vacancies relative to non-green vacancies of the same ISCO-08 sub-major group, excluding terms already in the ILO dictionaries. A starting point for a national green skills taxonomy, to be reviewed by experts.</p>
    {table_html(t19s)}
    <h2>7. Validation and quality assurance</h2>
    {"<p>Context check of the most frequent green terms (share of sampled occurrences used in a green sense; terms below 75% are handled through the exception list):</p>" + table_html(tv) if tv is not None else ""}
    {"<p>Boilerplate sensitivity: company text repeated across many postings can inflate green matches. Results with repeated sentences removed:</p>" + table_html(tb) if tb is not None else ""}
    <h2>8. Reproduce</h2>
    <p>Clone the repository, download the Kaggle dataset into <code>data/</code>, install <code>requirements.txt</code> and run the numbered scripts in <code>src/</code> in order. Every intermediate file, threshold and rule is set in <code>config.yaml</code>; the README is written as an implementation guide for a national institution.</p>
    <footer>Dictionaries © International Labour Organization 2025, reproduced from the ILO Research Briefs under CC BY 4.0. Vacancy data: Kaggle "LinkedIn Job Postings (2023–2024)", CC BY-SA 4.0. Code: MIT. This is an independent exercise and does not represent the views of the ILO or of the author's employers.</footer>
    </body></html>"""]
    (D / "index.html").write_text("\n".join(parts), encoding="utf-8")
    print("wrote", D / "index.html")

if __name__ == "__main__":
    main()

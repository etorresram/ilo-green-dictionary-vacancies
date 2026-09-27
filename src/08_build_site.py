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

# Colour substitutions applied to the Plotly HTML written by step 6 (plotly_white template) so that the
# figures sit on the dark page without re-running the pipeline. Series colours keep their ordering:
# "green" becomes a mid green that reads on a dark background and "darker green" stays the deeper shade.
_DARK = [('"paper_bgcolor":"white"', '"paper_bgcolor":"rgba(0,0,0,0)"'), ('"plot_bgcolor":"white"', '"plot_bgcolor":"rgba(0,0,0,0)"'),
         ('"bgcolor":"white"', '"bgcolor":"#1c2126"'), ('"color":"#2a3f5f"', '"color":"#e3e7ea"'),
         ('"gridcolor":"#EBF0F8"', '"gridcolor":"#2b3238"'), ('"gridcolor":"#DFE8F3"', '"gridcolor":"#2b3238"'), ('"gridcolor":"#C8D4E3"', '"gridcolor":"#2b3238"'),
         ('"linecolor":"#EBF0F8"', '"linecolor":"#3a444c"'), ('"linecolor":"#A2B1C6"', '"linecolor":"#3a444c"'), ('"linecolor":"#C8D4E3"', '"linecolor":"#3a444c"'),
         ('"zerolinecolor":"#EBF0F8"', '"zerolinecolor":"#3a444c"'), ('"color":"white"', '"color":"#1c2126"'),
         ('"color":"#2E7D32"', '"color":"#66BB6A"'), ('"color":"#1B5E20"', '"color":"#2E7D32"'),
         ('"line":{"dash":"dash"}', '"line":{"dash":"dash","color":"#e3e7ea"}'), ('"mapbox":{"style":"light"}', '"mapbox":{"style":"dark"}')]

def dark(fig_html):
    for a, b in _DARK: fig_html = fig_html.replace(a, b)
    return fig_html

def main():
    c = cfg(); T = path(c["output"]["tables"]); F = path(c["output"]["figures"]); D = path(c["output"]["site"]); D.mkdir(exist_ok=True)
    s = json.load(open(T / "summary.json"))
    fig = {n: dark(open(F / f"{n}.html").read()) for n in ["f01_green_by_isco_major", "f02_green_by_isic_section", "f03_domains", "f04_skills_green_vs_nongreen", "f05_wages_by_isco_major", "f06_intensity"]}
    fig["f07"] = dark(open(F / "f07_green_by_month.html").read()) if (F / "f07_green_by_month.html").exists() else ""
    cp = c.get("corpus", {}); cur = cp.get("currency", "USD"); key = cp.get("key", "us_linkedin")
    other = ('<p class="note">Two corpora are available: <a href="../">United States (LinkedIn, Kaggle)</a> and <a href="./">Malaysia (JobStreet, Hugging Face)</a>. Same code, same dictionaries, different exception-list status.</p>' if key != "us_linkedin"
             else '<p class="note">Two corpora are available: <a href="./">United States (LinkedIn, Kaggle)</a> and <a href="malaysia/">Malaysia (JobStreet, Hugging Face)</a>, an ASEAN member state with a five-month series. Same code, same dictionaries.</p>')
    t0 = pd.read_csv(T / "t00_sample_construction.csv"); t2 = pd.read_csv(T / "t02_occupation_mapping_coverage.csv")
    t10 = pd.read_csv(T / "t10_green_shade_overall.csv"); t14 = pd.read_csv(T / "t14_domains.csv"); t16 = pd.read_csv(T / "t16_wages_by_shade.csv")
    t11b = pd.read_csv(T / "t11b_green_by_isco_major_sensitivity.csv"); t19 = pd.read_csv(T / "t19_candidate_technical_green_skills_by_isco_submajor.csv")
    tv = pd.read_csv(T / "t20_context_check_results.csv") if (T / "t20_context_check_results.csv").exists() else None
    tb = pd.read_csv(T / "t21_boilerplate_sensitivity.csv") if (T / "t21_boilerplate_sensitivity.csv").exists() else None
    t19s = t19.groupby("isco08_submajor_label")["expression"].apply(lambda x: ", ".join(x.head(10))).reset_index().rename(columns={"isco08_submajor_label": "ISCO-08 sub-major group", "expression": "Top candidate expressions (over-represented in green vacancies)"})
    css = """
    :root{color-scheme:dark;--bg:#14181c;--surface:#1c2126;--text:#e3e7ea;--muted:#a9b3bb;--line:#2b3238;--green:#66BB6A;--green-bg:#1c2a1e;--amber:#f9a825;--amber-bg:#2b2410;--link:#8fd19e}
    html{background:var(--bg)} body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:1000px;margin:0 auto;padding:24px;background:var(--bg);color:var(--text);line-height:1.5}
    a{color:var(--link)} h1{font-size:1.7rem;margin-bottom:.2rem} h2{font-size:1.25rem;border-bottom:2px solid var(--green);padding-bottom:4px;margin-top:2.2rem}
    .sub{color:var(--muted)} .kpis{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0} .kpi{flex:1 1 180px;background:var(--green-bg);border-left:4px solid var(--green);padding:10px 14px;border-radius:4px}
    .kpi b{font-size:1.5rem;display:block} .tbl{border-collapse:collapse;font-size:.85rem;margin:10px 0;width:100%} .tbl th{background:var(--surface);text-align:left;padding:5px 8px;border-bottom:1px solid var(--green)} .tbl td{padding:4px 8px;border-bottom:1px solid var(--line)}
    .note{background:var(--amber-bg);border-left:4px solid var(--amber);padding:8px 12px;font-size:.9rem} .fig{margin:12px 0 28px;background:var(--surface);border-radius:6px;padding:6px} code{background:var(--surface);padding:1px 4px;border-radius:3px} footer{margin-top:40px;font-size:.85rem;color:var(--muted)}
    """
    kp = f"""
    <div class="kpis">
      <div class="kpi"><span>Vacancies analysed</span><b>{s['n_postings']:,}</b></div>
      <div class="kpi"><span>Green vacancies (at least one green task)</span><b>{100*s['green_share']:.1f}%</b></div>
      <div class="kpi"><span>Darker green (share of green tasks above the mean)</span><b>{100*s['darker_share']:.1f}%</b></div>
      <div class="kpi"><span>Median posted wage, green vs non-green ({cur})</span><b>{s['median_wage_green']:,.0f} vs {s['median_wage_nongreen']:,.0f}</b></div>
    </div>"""
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark">
    <title>ILO Green Dictionary applied to online vacancies</title><style>{css}</style></head><body>
    <h1>Measuring green jobs in online vacancies with the ILO Green Dictionary</h1>
    <p class="sub">A documented replication of the ILO methodology (Delaporte, Escudero and Adamczyk 2025; Adamczyk et al. 2025) on a public corpus of {s['n_postings']:,} English-language job postings: <b>{html.escape(cp.get('name', ''))}</b> (<a href="{cp.get('source_url', '#')}">source</a>, {html.escape(cp.get('licence', ''))}). Code, dictionaries and this page: <a href="https://github.com/etorresram/ilo-green-dictionary-vacancies">github.com/etorresram/ilo-green-dictionary-vacancies</a>. Author: Eric Torres Ramírez.</p>
    {other}
    {kp}
    <p class="note"><b>Read this first.</b> Time coverage: {html.escape(cp.get('n_months_note', ''))}. Vacancies come from one platform in one country and there are no applicants' profiles, so demand cannot be compared with supply. The skills variables use the <em>selected</em> keywords published in the ILO brief, not the full taxonomy. {"The exception list was validated on the US corpus and reused here; a corpus-specific context check is pending." if key != "us_linkedin" else ""} All figures illustrate the workflow; none is an estimate of a national labour market.</p>
    <h2>1. What was done</h2>
    <ol>
      <li><b>Data preparation.</b> Duplicate and empty postings removed; posted salaries annualised; platform industry or category labels mapped to ISIC Rev. 4 sections with a reviewed file.</li>
      <li><b>Text pre-processing</b> in the ILO sequence: tokenisation, normalisation, stop-word removal (keeping stop words inside dictionary expressions), lemmatisation (spaCy). Dictionary expressions go through the same pipeline, so matching is lemma-to-lemma on full words.</li>
      <li><b>Green task variables</b>: 9 sustainability domains, binary and counts; a vacancy is green if it matches at least one domain.</li>
      <li><b>Skills variables</b>: 15 subcategories (cognitive, socio-emotional, manual).</li>
      <li><b>Green share and shade</b>: share of green tasks among all matched skills and tasks; non-green (0), lighter green (below the mean among green vacancies), darker green (at or above).</li>
      <li><b>Occupation coding</b>: job title → O*NET-SOC → SOC 2010 → ISCO-08 through official crosswalks, with every admissible code kept and an explicit assignment rule.</li>
      <li><b>Validation</b>: context check of frequent terms (75% rule), a blind hand-coding sample, and a boilerplate sensitivity test.</li>
    </ol>
    {table_html(t0)}
    {"<h2>2. Green vacancies over time</h2><div class='fig'>" + fig["f07"] + "</div><p>Monthly share of vacancies with at least one green task and share of darker-green vacancies; hover for the number of postings per month. Tables t23 and t24 give the same by month and ISCO-08 major group.</p>" if fig["f07"] else ""}
    <h2>{"3" if fig["f07"] else "2"}. Green vacancies by occupation and industry</h2>
    <div class="fig">{fig['f01_green_by_isco_major']}</div>
    <p>Occupation coding coverage and ambiguity:</p>{table_html(t2)}
    <p>Sensitivity of the occupational profile to the assignment rule for titles with more than one admissible ISCO-08 code (main rule vs alternative rule):</p>
    {table_html(t11b, ["isco08_major_label", "n", "green_share", "green_share_alt_rule", "abs_diff_pp"])}
    <div class="fig">{fig['f02_green_by_isic_section']}</div>
    <h2>{"4" if fig["f07"] else "3"}. Shade of green and sustainability domains</h2>
    {table_html(t10)}
    <div class="fig">{fig['f06_intensity']}</div>
    <div class="fig">{fig['f03_domains']}</div>
    <h2>{"5" if fig["f07"] else "4"}. Skills requirements in green versus non-green vacancies</h2>
    <div class="fig">{fig['f04_skills_green_vs_nongreen']}</div>
    <h2>{"6" if fig["f07"] else "5"}. Posted wages</h2>
    <p>Posted annual wages ({cur}, {s['n_with_wage']:,} vacancies with a salary field, midpoint of the posted range, annualised). Nominal values; over a period of a few months deflation changes nothing material, and the code has a hook for a CPI deflator when the series is longer.</p>
    {table_html(t16)}
    <div class="fig">{fig['f05_wages_by_isco_major']}</div>
    <h2>{"7" if fig["f07"] else "6"}. Candidate occupation-specific technical green skills</h2>
    <p>Expressions over-represented in green vacancies relative to non-green vacancies of the same ISCO-08 sub-major group, excluding terms already in the ILO dictionaries. A starting point for a national green skills taxonomy, to be reviewed by experts.</p>
    {table_html(t19s)}
    <h2>{"8" if fig["f07"] else "7"}. Validation and quality assurance</h2>
    {"<p>Context check of the most frequent green terms (share of sampled occurrences used in a green sense; terms below 75% are handled through the exception list):</p>" + table_html(tv) if tv is not None else ""}
    {"<p>Boilerplate sensitivity: company text repeated across many postings can inflate green matches. Results with repeated sentences removed:</p>" + table_html(tb) if tb is not None else ""}
    <h2>{"9" if fig["f07"] else "8"}. Reproduce</h2>
    <p>Clone the repository, download the vacancy dataset into <code>data/</code>, install <code>requirements.txt</code> and run the numbered scripts in <code>src/</code> in order. Every intermediate file, threshold and rule is set in <code>config.yaml</code>; the README is written as an implementation guide for a national institution.</p>
    <footer>Dictionaries © International Labour Organization 2025, reproduced from the ILO Research Briefs under CC BY 4.0. Vacancy data: {html.escape(cp.get('name', ''))}, {html.escape(cp.get('licence', ''))}. Code: MIT. This is an independent exercise and does not represent the views of the ILO or of the author's employers.</footer>
    </body></html>"""]
    (D / "index.html").write_text("\n".join(parts), encoding="utf-8")
    print("wrote", D / "index.html")

if __name__ == "__main__":
    main()

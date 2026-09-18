# Measuring green jobs in online vacancies with the ILO Green Dictionary

A documented, reproducible implementation of the ILO methodology for measuring green tasks, skills
and the "shade of green" of job vacancies from free text, applied to a public English-language
corpus of job postings. It is written as an **implementation guide**: every step states what is
done, why, which choice is the ILO's and which is an adaptation, and how a national institution
would rerun it on its own data.

**Results page:** https://etorresram.github.io/ilo-green-dictionary-vacancies/  
**Author:** Eric Torres Ramírez · **Status:** demonstration, September 2026

> The corpus is a one-month snapshot of vacancies from one country and one platform. It cannot
> show trends over time nor compare demand (vacancies) with supply (applicants' profiles). The
> skills variables use the *selected* keywords published by the ILO, not the full taxonomy. Every
> number here illustrates the workflow; none is an estimate of a labour market.

## Methodology being implemented

| Component | Source | What is replicated |
|---|---|---|
| Green dictionary, 9 sustainability domains, green share and shade of green | Delaporte, Escudero and Adamczyk (2025), *Measuring the Greenness of Jobs in Emerging Economies: A Big Data Text Analysis Approach*, ILO Research Brief, [doi:10.54394/JKGV7887](https://doi.org/10.54394/JKGV7887) | Full dictionary (Table A.1), pre-processing sequence, full-word lemma matching, context check with the 75% rule, share of green tasks and the three-way classification |
| Skills taxonomy, 15 subcategories | Adamczyk, Boehmer, Delaporte, Escudero and Liepmann (2025), *Developing a New Method to Uncover Skills Trends in Emerging Economies Using Online Data and NLP Techniques*, ILO Research Brief, [doi:10.54394/HQQX3200](https://doi.org/10.54394/HQQX3200) | Selected keywords (Table A.1) and the same matching; partial by construction |
| Occupation coding to ISCO-08 | O*NET 29.1 titles; BLS SOC 2010–2018 crosswalk; BLS/SOCPC ISCO-08–SOC 2010 crosswalk | Title matching and a chain of official crosswalks with all admissible codes kept |

## Repository layout

```
config.yaml                 every path, threshold and rule
dictionaries/               ILO dictionaries transcribed from the briefs, exception list, industry map
crosswalks/                 O*NET, BLS and ILO classification files (public)
src/01_prepare_data.py      duplicates, wages, industry -> ISIC section
src/02_preprocess_text.py   tokenise, normalise, stop words, lemmatise (slow; cached)
src/03_green_and_skills_variables.py   dictionary matching, green share, shade
src/04_occupation_mapping.py           title -> ISCO-08 with explicit assignment rule
src/05_validation_samples.py           context-check snippets and blind hand-coding sample
src/05b_boilerplate_sensitivity.py     effect of repeated corporate text
src/06_descriptives.py                 tables (output/tables) and figures (output/figures)
src/07_technical_green_skills.py       candidate occupation-specific green skills
src/08_build_site.py                   docs/index.html (GitHub Pages)
validation/                 files coded by hand and their results
output/                     aggregate tables and figures only (no microdata)
WORKFLOW.md                 diagram of the pipeline
QA_CHECKLIST.md             checks to tick before sharing results
```

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# put the vacancy files under ../data/ (see config.yaml) — here: Kaggle "LinkedIn Job Postings (2023-2024)"
python src/01_prepare_data.py
python src/02_preprocess_text.py          # ~25 min for 110k postings on a laptop, 4 processes
python src/03_green_and_skills_variables.py
python src/04_occupation_mapping.py       # ~10 min (fuzzy title matching)
python src/05_validation_samples.py       # then code the two CSVs in validation/ by hand
python src/05b_boilerplate_sensitivity.py
python src/06_descriptives.py
python src/07_technical_green_skills.py
python src/08_build_site.py
```

Everything after step 02 runs in minutes, so dictionaries, exception rules and thresholds can be
revised and re-run cheaply. To apply the pipeline to another corpus, change the `data:` block in
`config.yaml` and the column names in `src/01_prepare_data.py`; nothing else depends on the source.

## Step-by-step guide

### 1. Data preparation
Duplicates are identified on title + company + description. Posted wages are annualised from the
stated pay period (hourly × 2,080; weekly × 52; monthly × 12); values below 10,000 or above
1,000,000 USD are set to missing and counted, never trimmed silently. Platform industry labels are
mapped to ISIC Rev. 4 sections with a reviewed file (`dictionaries/linkedin_industry_to_isic_section.csv`).
For a national application this is where PSIC/PSOC or any national codes are mapped to ISIC/ISCO
with the official correspondence tables.

### 2. Text pre-processing (ILO sequence)
Lower-casing and removal of special characters; tokenisation; stop-word removal, **keeping stop
words that occur inside dictionary expressions** (for example "with" in "interact with others");
lemmatisation with spaCy `en_core_web_sm`. Hyphenated compounds are split ("self-motivated" →
"self motivated") on both sides. A small map corrects British lemmas returned by spaCy
("instal" → "install") so that dictionary and text agree. Dictionary expressions are lemmatised
with exactly the same function.

### 3. Matching and variables
Every 1- to 5-gram of lemmas is looked up in the lemmatised dictionary, so matches are on full
words, never on roots or substrings (the brief's stated difference from Granata and Posadas 2024).
Per posting: one count and one binary indicator per green domain (G01–G09) and per skills
subcategory (S01–S15). `green_any` = at least one green domain. `green_share` = green matches /
(green + skills matches), the share of green tasks among all skills and tasks mentioned. Shade:
non-green (share 0), lighter green (below the mean share among green vacancies), darker green
(at or above). The same file stores the matched terms per posting for validation.

### 4. Occupation coding
Job titles are matched to O*NET occupation and alternate titles (exact, then exact after removing
seniority and contract modifiers, then token-sort fuzzy matching at a 90 threshold). O*NET-SOC
2019 → SOC 2018 → SOC 2010 (BLS crosswalk) → ISCO-08 (BLS/SOCPC crosswalk). Codes are handled as
strings so that armed-forces codes keep their leading zero. When several ISCO-08 codes are
admissible, the assignment rule is: the code reached by most SOC links, ties broken by the
similarity between the job title and the ISCO unit-group title, then by the lowest code. The
alternative assignment (highest admissible code) is stored and the occupational profile is re-run
under it (`output/tables/t11b_...`). This makes the definitional uncertainty visible instead of
hiding it in a choice.

### 5. Validation
`validation/context_check_snippets.csv` holds 40 occurrences with context for every frequent green
term; a reviewer marks each as green-sense or not, and terms below 75% are handled through
`dictionaries/exceptions_en_us.csv` (drop the term, or drop the match when a context pattern is
present). `validation/vacancy_sample_for_hand_coding.csv` is a stratified blind sample for
precision and recall by domain. `05b` measures how much of the green signal comes from corporate
boilerplate repeated across postings, a source of false positives that grows with the size of
large advertisers.

### 6. Outputs
`output/tables` contains every table behind the results page (`t10`–`t21`), `output/figures`
the PNG and interactive HTML figures, and `docs/index.html` the page. Items in the ILO ToR that
need a time series or applicants' data are not produced; the functions accept a month key and a
supply-side file so that they can be switched on when the data exist.

## Adapting to another country (checklist)
1. Map national occupation and industry codes to ISCO-08 and ISIC Rev. 4 with the official tables;
   log every code with more than one destination and the rule used.
2. Measure the language mix. If a second language is common, translate the dictionaries with
   validated synonyms and build a language-specific exception list (the ILO did this for Spanish,
   Portuguese and Russian).
3. Rebuild the exception list: company names, locations, brands and boilerplate that match green
   terms in the new corpus.
4. Re-run the context check and the blind sample; do not reuse another country's precision figures.
5. Separate statutory benefits from voluntary amenities before any job-quality analysis.
6. Keep the dictionaries versioned; record the version and date in every output.

## Licences and attribution
Dictionaries © International Labour Organization 2025, reproduced from the Research Briefs under
CC BY 4.0. Vacancy data: Kaggle "LinkedIn Job Postings (2023–2024)" by Arsh Koneru, CC BY-SA 4.0
(not redistributed here). O*NET® 29.1 © National Center for O*NET Development, CC BY 4.0. Code: MIT.
This is an independent exercise; it does not represent the views of the ILO or of the author's employers.

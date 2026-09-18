# Quality assurance checklist

Tick every item before results are shared. Items marked (ILO) come from the ILO Research Briefs;
items marked (added) are additional checks introduced in this implementation.

## Data
- [ ] Row counts recorded at each step (`output/tables/t00_sample_construction.csv`).
- [ ] Duplicate postings removed on title + company + description; share of duplicates reported.
- [ ] Text length distribution inspected; postings with fewer than 50 characters excluded and counted.
- [ ] Language mix measured (share of non-English postings) and reported as a coverage limit.
- [ ] Time coverage stated; if a single month, "over time" items are marked as not applicable.

## Dictionaries
- [ ] Green dictionary loaded unchanged from the published table; row count matches `dictionaries/README.md`.
- [ ] Skills taxonomy loaded; partial coverage stated in every output that uses it.
- [ ] Both dictionaries pass through the same pre-processing as the text (ILO).
- [ ] Every exception rule has a reason and evidence (`dictionaries/exceptions_en_us.csv`).

## Matching
- [ ] Full-word, lemma-level matching; no stem or substring matching (ILO).
- [ ] Stop words inside dictionary expressions are protected from removal (added).
- [ ] Longest dictionary expression length equals `text.max_ngram` in `config.yaml`.
- [ ] Green share denominator is green + skills matches (ILO definition); shade cut-off is the mean among green vacancies (ILO).

## Occupation and industry coding
- [ ] ISCO-08 codes are strings with leading zeros (armed forces 0110, 0210, 0310).
- [ ] Coverage table produced (`t02`); fuzzy matches spot-checked on a random sample of 50 titles.
- [ ] Number of admissible ISCO-08 codes per title stored; assignment rule stated in the script docstring.
- [ ] Descriptive results re-run under the alternative assignment (`t11b`); differences reported.
- [ ] Industry mapping file reviewed; unmapped industries = 0.

## Validation
- [ ] Context check: 40 snippets per frequent term coded; terms below 75% green sense handled (ILO).
- [ ] Blind hand-coding sample coded by a person who did not see the machine labels; precision and recall by domain reported.
- [ ] Boilerplate sensitivity run; share of green postings that depend on repeated corporate text reported (added).

## Outputs
- [ ] Every figure states n and the data source.
- [ ] Wages: currency, period and deflator stated; implausible values set to missing, not trimmed silently.
- [ ] Results page builds from `output/` without manual edits.
- [ ] Repository has no microdata; `data/` is git-ignored.

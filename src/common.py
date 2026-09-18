"""Shared helpers: configuration, dictionary loading, text pre-processing and dictionary matching.

The pre-processing follows the sequence described in Delaporte, Escudero and Adamczyk (2025) and
Adamczyk et al. (2025): tokenisation, normalisation (lower case, special characters removed),
stop-word removal (keeping stop words that occur inside dictionary expressions) and lemmatisation.
Dictionary expressions are passed through exactly the same pipeline, so that matching is done
lemma-to-lemma on full words, never on word roots or partial strings.
"""
from __future__ import annotations
import re, csv, functools
from pathlib import Path
import yaml
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

@functools.lru_cache(maxsize=1)
def cfg() -> dict:
    with open(ROOT / "config.yaml") as f:
        c = yaml.safe_load(f)
    return c

def path(rel: str) -> Path:
    return (ROOT / rel).resolve()

def work_dir() -> Path:
    p = path(cfg()["data"]["work_dir"]); p.mkdir(parents=True, exist_ok=True); return p

# ----------------------------------------------------------------------------- text
_NON_ALNUM = re.compile(r"[^a-z0-9\s\-]")
_HYPHEN = re.compile(r"(?<=[a-z])-(?=[a-z])")

def normalise(text: str) -> str:
    """Lower case, join hyphenated compounds with a space, drop everything that is not a letter,
    digit or space, and collapse whitespace."""
    t = (text or "").lower().replace("’", "'")
    t = _HYPHEN.sub(" ", t)
    t = _NON_ALNUM.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()

# spaCy returns British lemmas for a few verbs; map them to the American base form so that the
# dictionary term "install" matches "installing". Both sides go through the same map.
LEMMA_FIX = {"instal": "install", "enrol": "enroll", "fulfil": "fulfill", "cancelled": "cancel",
             "labour": "labor", "programme": "program", "datum": "data"}

@functools.lru_cache(maxsize=1)
def nlp():
    import spacy
    m = spacy.load(cfg()["text"]["spacy_model"], disable=["parser", "ner"])
    return m

@functools.lru_cache(maxsize=1)
def protected_stopwords() -> frozenset:
    """Stop words that appear inside dictionary expressions and must therefore be kept."""
    from spacy.lang.en.stop_words import STOP_WORDS
    words = set()
    for d in (load_green(), load_skills()):
        for t in d["term"]:
            words.update(t.split())
    return frozenset(w for w in words if w in STOP_WORDS)

def lemmatise_docs(texts, n_process=None, batch_size=None):
    """Yield one list of lemmas per input text, applying the full pre-processing sequence."""
    from spacy.lang.en.stop_words import STOP_WORDS
    keep = protected_stopwords()
    c = cfg()["text"]
    n_process = n_process or c["n_process"]; batch_size = batch_size or c["batch_size"]
    for doc in nlp().pipe((normalise(t) for t in texts), n_process=n_process, batch_size=batch_size):
        out = []
        for tok in doc:
            if tok.is_space or tok.is_punct:
                continue
            lem = tok.lemma_.lower().strip()
            lem = LEMMA_FIX.get(lem, lem)
            if not lem:
                continue
            if lem in STOP_WORDS and lem not in keep:
                continue
            out.append(lem)
        yield out

def lemmatise_terms(terms):
    """Lemmatise dictionary expressions with the same pipeline, one expression at a time."""
    return [tuple(l) for l in lemmatise_docs(terms, n_process=1, batch_size=64)]

# ----------------------------------------------------------------------------- dictionaries
def load_green() -> pd.DataFrame:
    return pd.read_csv(path(cfg()["dictionaries"]["green"]))

def load_skills() -> pd.DataFrame:
    return pd.read_csv(path(cfg()["dictionaries"]["skills"]))

def load_exceptions() -> pd.DataFrame:
    p = path(cfg()["dictionaries"]["exceptions"])
    if not p.exists():
        return pd.DataFrame(columns=["dictionary", "term", "rule", "pattern", "reason", "evidence"])
    return pd.read_csv(p).fillna("")

class Matcher:
    """Full-word, lemma-level matcher for multi-word expressions.

    Each expression is stored as a tuple of lemmas. For a document (list of lemmas) every n-gram
    up to `max_ngram` is looked up in the expression set. Longer matches do not suppress shorter
    ones, mirroring a keyword count; an exception file can (a) drop a term entirely or (b) drop a
    match when a longer context pattern is present in the same document.
    """
    def __init__(self, terms: pd.DataFrame, group_col: str, dictionary_name: str, max_ngram: int = 5):
        self.dictionary_name = dictionary_name
        self.group_col = group_col
        exc = load_exceptions()
        exc = exc[exc["dictionary"] == dictionary_name]
        dropped = set(exc.loc[exc["rule"] == "drop_term", "term"])
        terms = terms[~terms["term"].isin(dropped)].reset_index(drop=True)
        lem = lemmatise_terms(terms["term"].tolist())
        self.expr = {}            # lemma tuple -> list of (term, group)
        for (t, g), l in zip(terms[["term", group_col]].itertuples(index=False), lem):
            if not l:
                continue
            self.expr.setdefault(l, []).append((t, g))
        self.max_ngram = min(max_ngram, max(len(k) for k in self.expr))
        # context exclusions: term -> list of lemma tuples that void the match
        self.context_exc = {}
        for r in exc[exc["rule"] == "drop_if_context"].itertuples(index=False):
            self.context_exc.setdefault(r.term, []).extend(lemmatise_terms([r.pattern]))
        self.groups = sorted(terms[group_col].unique())

    def ngrams(self, lemmas):
        n = len(lemmas)
        for k in range(1, self.max_ngram + 1):
            for i in range(0, n - k + 1):
                yield tuple(lemmas[i:i + k])

    def match(self, lemmas):
        """Return list of (term, group) for every occurrence in the document."""
        hits = []
        grams = None
        for g in self.ngrams(lemmas):
            if g in self.expr:
                for term, group in self.expr[g]:
                    if term in self.context_exc:
                        if grams is None:
                            grams = set(self.ngrams(lemmas))
                        if any(p in grams for p in self.context_exc[term]):
                            continue
                    hits.append((term, group))
        return hits


# ----------------------------------------------------------------------------- boilerplate
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")

def boilerplate_sentences(descriptions, min_postings=20, min_words=6):
    """Return (sentence set, per-document sentence lists). A sentence is boilerplate when the same
    normalised sentence appears in at least `min_postings` distinct documents. Used by the
    sensitivity test (05b) and to exclude repeated corporate text from the candidate-skills list (07)."""
    import collections
    freq = collections.Counter(); per_doc = []
    for d in descriptions:
        ss = [normalise(x) for x in _SENT.split(d or "")]
        ss = [x for x in ss if len(x.split()) >= min_words]
        per_doc.append(ss); freq.update(set(ss))
    return {x for x, n in freq.items() if n >= min_postings}, per_doc

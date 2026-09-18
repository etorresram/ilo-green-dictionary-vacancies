"""Step 2. Pre-process the text of every posting (title + description) into a list of lemmas,
following the ILO sequence. Writes data/work/lemmas.parquet with columns job_id, lemmas, n_tokens.
Slow step (spaCy over ~110k long ads); run once and cache."""
import sys, time
import pandas as pd, pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import cfg, work_dir, lemmatise_docs

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    df = pd.read_parquet(work_dir() / "postings_clean.parquet", columns=["job_id", "text"])
    if limit:
        df = df.head(limit)
    t0 = time.time()
    out_path = work_dir() / ("lemmas.parquet" if not limit else f"lemmas_sample{limit}.parquet")
    writer = None
    chunk = 5000
    for start in range(0, len(df), chunk):
        part = df.iloc[start:start + chunk]
        lem = list(lemmatise_docs(part["text"].tolist()))
        tbl = pa.table({"job_id": part["job_id"].values, "lemmas": lem, "n_tokens": [len(l) for l in lem]})
        if writer is None:
            writer = pq.ParquetWriter(out_path, tbl.schema)
        writer.write_table(tbl)
        print(f"{start + len(part):>7} / {len(df)}  {time.time() - t0:7.0f}s", flush=True)
    writer.close()
    print("done", out_path)


if __name__ == "__main__":
    main()

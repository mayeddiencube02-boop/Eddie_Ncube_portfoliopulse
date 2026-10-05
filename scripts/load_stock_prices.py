"""
Load daily stock prices from yfinance into Neon (Postgres).

- Creates schema `raw` and table `raw.stock_prices` if they don't exist.
- First run backfills from START_DATE; later runs only re-fetch the last
  LOOKBACK_DAYS days. Rows are upserted on (ticker, price_date), so the
  script is safe to run repeatedly (idempotent).
- Exits with a non-zero code on any failure, so GitHub Actions fails loudly.
"""
import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import psycopg2
import yfinance as yf
from dotenv import load_dotenv
from psycopg2.extras import execute_values

TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL"]
START_DATE = "2026-04-01"   # first-run backfill start
LOOKBACK_DAYS = 10          # re-fetch window on later runs (covers holidays/late fixes)

DDL = """
create schema if not exists raw;

create table if not exists raw.stock_prices (
    ticker      text        not null,
    price_date  date        not null,
    open        numeric(12,4),
    high        numeric(12,4),
    low         numeric(12,4),
    close       numeric(12,4) not null,
    volume      bigint,
    loaded_at   timestamptz not null default now(),
    primary key (ticker, price_date)
);
"""

UPSERT = """
insert into raw.stock_prices (ticker, price_date, open, high, low, close, volume)
values %s
on conflict (ticker, price_date) do update set
    open = excluded.open,
    high = excluded.high,
    low = excluded.low,
    close = excluded.close,
    volume = excluded.volume,
    loaded_at = now();
"""


def fetch_ticker(ticker, start, end, retries=3):
    """Download one ticker at a time (parallel downloads caused cache-lock errors)."""
    for attempt in range(1, retries + 1):
        df = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            df["ticker"] = ticker
            return df
        print(f"  {ticker}: empty result (attempt {attempt}/{retries}), retrying...")
        time.sleep(3)
    raise RuntimeError(f"No data returned for {ticker} between {start} and {end}")


def to_rows(df):
    rows = []
    for r in df.itertuples(index=False):
        if pd.isna(r.Close):
            continue
        rows.append(
            (
                r.ticker,
                pd.Timestamp(r.Date).date(),
                None if pd.isna(r.Open) else float(r.Open),
                None if pd.isna(r.High) else float(r.High),
                None if pd.isna(r.Low) else float(r.Low),
                float(r.Close),
                None if pd.isna(r.Volume) else int(r.Volume),
            )
        )
    return rows


def main():
    load_dotenv()
    url = os.environ.get("NEON_DATABASE_URL")
    if not url:
        sys.exit("NEON_DATABASE_URL is not set (check your .env or GitHub Secrets)")

    conn = psycopg2.connect(url)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute("select max(price_date) from raw.stock_prices")
            latest = cur.fetchone()[0]

        if latest is None:
            start = START_DATE
            print(f"Empty table: backfilling from {start}")
        else:
            start = (latest - timedelta(days=LOOKBACK_DAYS)).isoformat()
            print(f"Latest stored date is {latest}: refreshing from {start}")

        end = (date.today() + timedelta(days=1)).isoformat()  # end is exclusive

        total = 0
        for t in TICKERS:
            print(f"Fetching {t}...")
            rows = to_rows(fetch_ticker(t, start, end))
            with conn, conn.cursor() as cur:
                execute_values(cur, UPSERT, rows)
            print(f"  {t}: upserted {len(rows)} rows")
            total += len(rows)

        with conn, conn.cursor() as cur:
            cur.execute(
                """
                select ticker, count(*), min(price_date), max(price_date)
                from raw.stock_prices
                group by ticker
                order by ticker
                """
            )
            print("\nraw.stock_prices summary:")
            for ticker, n, lo, hi in cur.fetchall():
                print(f"  {ticker:6} {n:4} rows  {lo} -> {hi}")
        print(f"\nDone. {total} rows upserted this run.")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"LOAD FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

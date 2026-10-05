import time
import pandas as pd
import yfinance as yf

# Reads trade_log.csv, replaces price_paid with the real closing price
# on each trade date, and writes trade_log_real.csv

trades = pd.read_csv("trade_log.csv", parse_dates=["date"])
tickers = trades["ticker"].unique().tolist()


def get_closes(ticker, retries=3):
    for attempt in range(retries):
        df = yf.download(
            ticker,
            start="2026-04-01",
            end="2026-10-01",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if not df.empty:
            close = df["Close"]
            # Newer yfinance returns a one-column DataFrame; flatten it
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            return close
        time.sleep(2)
    raise RuntimeError(f"Could not download data for {ticker}")


# One ticker at a time avoids the 'database is locked' cache error
closes = {}
for t in tickers:
    print(f"Downloading {t}...")
    closes[t] = get_closes(t)

prices = []
for d, t in zip(trades["date"], trades["ticker"]):
    series = closes[t]
    if d not in series.index or pd.isna(series.loc[d]):
        raise ValueError(f"No price found for {t} on {d.date()} (market closed?)")
    prices.append(round(float(series.loc[d]), 2))

trades["price_paid"] = prices
trades["date"] = trades["date"].dt.strftime("%Y-%m-%d")
trades.to_csv("trade_log_real.csv", index=False)
print(trades.to_string(index=False))
print("\nSaved trade_log_real.csv")

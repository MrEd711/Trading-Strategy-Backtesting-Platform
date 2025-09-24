#!/usr/bin/env python3
"""
Download OHLCV data for Ethereum (ETHUSDT) from Binance
and save it as a CSV that chart_viewer.py can read.
"""

import pathlib
import time
from argparse import ArgumentParser
from typing import List
import requests
import pandas as pd
from pandas_datareader import data as pdr


BINANCE_SPOT_KLINES = "https://api.binance.com/api/v3/klines"
SYMBOL = "ETHUSDT"
LIMIT  = 10000   # Binance max per request

def fetch_chunk(start_ms: int, interval: str) -> List[list]:  ## ← edited
    params = {
        "symbol":    SYMBOL,
        "interval":  interval,       ## ← edited
        "startTime": start_ms,
        "limit":     LIMIT,
    }
    r = requests.get(BINANCE_SPOT_KLINES, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def main():
    p = ArgumentParser()
    p.add_argument(
        "--days", "-d",
        type=int,
        default=20,
        help="Number of past days to fetch."
    )
    p.add_argument(
        "--interval", "-i",           ## ← edited
        default="15m",                ## ← edited
        help="Kline interval (e.g. 1m, 5m, 15m, 1h, 1d)."
    )
    p.add_argument(
        "--out", "-o",
        type=pathlib.Path,
        default=pathlib.Path("eth_15m.csv"),
        help="Output CSV filename"
    )
    args = p.parse_args()

    # compute ms timestamps
    end_ts_ms   = int(time.time() * 1000)
    start_ts_ms = end_ts_ms - args.days * 24 * 60 * 60 * 1000

    # fetch in chunks
    all_rows   = []
    fetch_from = start_ts_ms
    while fetch_from < end_ts_ms:
        chunk = fetch_chunk(fetch_from, args.interval)  ## ← edited
        if not chunk:
            break
        all_rows.extend(chunk)
        fetch_from = chunk[-1][6] + 1
        time.sleep(0.35)

    # to DataFrame
    df = pd.DataFrame(
        all_rows,
        columns=[
            "OpenTime","Open","High","Low","Close","Volume",
            "CloseTime","QuoteAssetVolume","NumberOfTrades",
            "TakerBuyBase","TakerBuyQuote","Ignore"
        ],
    )
    df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms")
    # Select columns and convert only numerical values to float
    df = df[["Date","Open","High","Low","Close","Volume"]]
    num_cols = ["Open","High","Low","Close","Volume"]
    df[num_cols] = df[num_cols].astype(float)

     # save ETH data
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} rows → {args.out}")

    # Fetch S&P 500
   # Fetch S&P 500
    start_date = df["Date"].iloc[0].strftime("%Y-%m-%d")
    end_date = df["Date"].iloc[-1].strftime("%Y-%m-%d")

    print(f"Fetching S&P 500 from {start_date} to {end_date}")
    try:
        sp500 = pdr.DataReader('^SPX', 'stooq', start=start_date, end=end_date)
        sp500 = sp500.sort_index()  # ascending by date
    except Exception as e:
        print(f"❌ Failed to fetch S&P 500 data: {e}")
        return

    if not sp500.empty:

        # Reset index to make Date a column
        sp500 = sp500.reset_index()
        
        # Select only the columns we need
        sp500 = sp500[['Date', 'Close']]
        
        # Ensure numeric type for Close
        sp500['Close'] = sp500['Close'].astype(float)
        
        # Calculate returns
        # Calculate cumulative percentage return (equity curve)
        first_close = sp500['Close'].iloc[0]
        sp500['Return_%'] = (sp500['Close'] / first_close - 1.0) * 100


        # Save to CSV
        sp500.to_csv("sp500.csv", index=False)
        print(f"✅ S&P 500 data saved → sp500.csv ({len(sp500)} rows)")
    else:
        print("❌ Failed to fetch S&P 500 data.")



if __name__ == "__main__":
    main()


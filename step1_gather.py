"""STEP 1 - Gather exchange rates and interest rates.

Downloads free data from FRED (no API key needed), converts every
exchange rate to "US dollars per 1 foreign unit", resamples to month-end,
and saves two clean files:

    data/fx_monthly.csv     USD per foreign unit, month-end
    data/rates_monthly.csv  3-month interest rate, annual %, monthly

Run:  python step1_gather.py          (live FRED data)
      python step1_gather.py --demo   (synthetic offline data)
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

import config

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def fetch_fred(series_id: str) -> pd.Series:
    """Download one FRED series as a date-indexed float Series."""
    resp = requests.get(FRED_CSV.format(sid=series_id), timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    date_col = df.columns[0]               # "observation_date" or "DATE"
    s = pd.to_numeric(df[series_id], errors="coerce")  # "." -> NaN
    s.index = pd.to_datetime(df[date_col])
    return s.dropna().rename(series_id)


def gather_live() -> tuple[pd.DataFrame, pd.DataFrame]:
    fx = {}
    for ccy, (sid, quote) in config.FX_SERIES.items():
        s = fetch_fred(sid)
        # Normalise the quote convention -- the classic silent bug.
        fx[ccy] = s if quote == "usd_per_fx" else 1.0 / s
        print(f"  FX   {ccy}: {sid:10s} last obs {s.index[-1].date()}")
    fx = pd.DataFrame(fx)
    fx["USD"] = 1.0
    fx = fx.resample("ME").last()

    rates = {}
    for ccy, sid in config.RATE_SERIES.items():
        s = fetch_fred(sid)
        rates[ccy] = s
        print(f"  RATE {ccy}: {sid:16s} last obs {s.index[-1].date()}")
    rates = pd.DataFrame(rates).resample("ME").last()
    return fx, rates


def gather_demo(seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic data with carry-trade-like behaviour, for offline use.

    High-rate currencies drift up slowly, then crash together in a few
    stress episodes -- the 'nickels in front of a steamroller' pattern.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range(config.START_DATE, "2026-09-30", freq="ME")
    base = {"USD": 2.5, "EUR": 1.5, "JPY": 0.1, "GBP": 2.8, "CHF": 0.3,
            "CAD": 2.4, "AUD": 4.0, "NZD": 4.3, "NOK": 2.9, "SEK": 1.4}
    rates, fx = {}, {}
    crash_months = {pd.Timestamp("2008-10-31"), pd.Timestamp("2008-11-30"),
                    pd.Timestamp("2020-03-31"), pd.Timestamp("2024-08-31")}
    for ccy, level in base.items():
        # Mean-reverting rate around each currency's typical level.
        r = np.empty(len(dates)); r[0] = level
        for i in range(1, len(dates)):
            r[i] = r[i-1] + 0.03 * (level - r[i-1]) + rng.normal(0, 0.15)
        rates[ccy] = np.clip(r, -0.75, None)
        if ccy == "USD":
            fx[ccy] = np.ones(len(dates))
            continue
        beta = (level - 2.0) / 2.0           # high yielders are crash-prone
        rets = rng.normal(0.0005 * beta, 0.025, len(dates))
        for i, d in enumerate(dates):
            if d in crash_months:
                rets[i] += -0.06 * beta
        fx[ccy] = np.exp(np.cumsum(rets)) * (0.01 if ccy == "JPY" else 1.0)
    return (pd.DataFrame(fx, index=dates)[config.CURRENCIES],
            pd.DataFrame(rates, index=dates)[config.CURRENCIES])


def quality_report(fx: pd.DataFrame, rates: pd.DataFrame) -> None:
    """Flag stale or missing data before anyone trades on it."""
    print("\nData quality check")
    latest = rates.index.max()
    for ccy in config.CURRENCIES:
        last_rate = rates[ccy].last_valid_index()
        gap = (latest.to_period("M") - last_rate.to_period("M")).n
        flag = "  <-- STALE, forward-filled" if gap > 2 else ""
        print(f"  {ccy}: rate last {last_rate.date()}{flag}")
    # Sanity check on quote conventions: 1 USD should buy >1 unit of
    # JPY/NOK/SEK, and <1 unit of GBP/EUR.
    usd_buys = 1.0 / fx.iloc[-1]
    print("  1 USD buys:", ", ".join(f"{c} {v:.2f}" for c, v in usd_buys.items() if c != "USD"))


def main(demo: bool = False) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    print("Gathering", "DEMO" if demo else "live FRED", "data...")
    fx, rates = gather_demo() if demo else gather_live()
    fx, rates = fx.loc[config.START_DATE:], rates.loc[config.START_DATE:]
    rates = rates.ffill(limit=6)
    common = fx.dropna(how="all").index.intersection(rates.dropna(how="all").index)
    fx, rates = fx.loc[common], rates.loc[common]
    quality_report(fx, rates)
    fx.to_csv(f"{config.DATA_DIR}/fx_monthly.csv")
    rates.to_csv(f"{config.DATA_DIR}/rates_monthly.csv")
    print(f"\nSaved {len(fx)} months to {config.DATA_DIR}/")


if __name__ == "__main__":
    main(demo="--demo" in sys.argv)

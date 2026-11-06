"""STEP 2 - Apply rules to pick the best carry trade.

Rules (all set in config.py):
  1. Rank currencies by interest rate.
  2. Go long the N_LONG highest, short the N_SHORT lowest, equal weights.
  3. Only trade if the rate spread is at least MIN_SPREAD_PCT.
  4. Optionally scale size so expected volatility ~ VOL_TARGET.

Output: output/target_trades.csv -- this month's target positions.

Run:  python step2_signal.py
"""
import os

import numpy as np
import pandas as pd

import config


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    fx = pd.read_csv(f"{config.DATA_DIR}/fx_monthly.csv", index_col=0, parse_dates=True)
    rates = pd.read_csv(f"{config.DATA_DIR}/rates_monthly.csv", index_col=0, parse_dates=True)
    return fx, rates


def raw_weights(rates_row: pd.Series,
                n_long: int = config.N_LONG,
                n_short: int = config.N_SHORT,
                min_spread: float = config.MIN_SPREAD_PCT) -> pd.Series:
    """Rules 1-3 for one month. Returns weights that sum to zero:
    +1/n_long on each long currency, -1/n_short on each short."""
    r = rates_row.dropna().sort_values(ascending=False)
    w = pd.Series(0.0, index=rates_row.index)
    if len(r) < n_long + n_short:
        return w
    longs, shorts = r.index[:n_long], r.index[-n_short:]
    spread = r[longs].mean() - r[shorts].mean()
    if spread < min_spread:
        return w                      # not enough carry to be worth the risk
    w[longs] = 1.0 / n_long
    w[shorts] = -1.0 / n_short
    return w


def currency_returns(fx: pd.DataFrame, rates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Next-month USD return from holding each currency, split in two:
    carry = interest earned (annual % / 12), spot = exchange-rate change."""
    spot = fx.pct_change().shift(-1)          # move from month t to t+1
    carry = rates / 100.0 / 12.0              # rate known at month t
    return carry, spot


def vol_scale(gross_returns: pd.Series,
              target: float | None = config.VOL_TARGET,
              lookback: int = config.VOL_LOOKBACK_MONTHS) -> pd.Series:
    """Rule 4: size each month using only PAST volatility (no peeking)."""
    if target is None:
        return pd.Series(1.0, index=gross_returns.index)
    realised = gross_returns.rolling(lookback).std().shift(1) * np.sqrt(12)
    return (target / realised).clip(upper=2.0).fillna(1.0)


def build_weights(fx: pd.DataFrame, rates: pd.DataFrame, **rule_kwargs) -> pd.DataFrame:
    """Rules 1-3 applied every month in history."""
    return rates.apply(lambda row: raw_weights(row, **rule_kwargs), axis=1)


def main() -> pd.DataFrame:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    fx, rates = load_data()
    weights = build_weights(fx, rates)

    # Position size for THIS month uses the strategy's past volatility.
    carry, spot = currency_returns(fx, rates)
    gross = (weights * (carry + spot)).sum(axis=1).shift(1).dropna()
    scale = vol_scale(gross).iloc[-1] if config.VOL_TARGET else 1.0

    today = rates.index[-1]
    w = weights.loc[today] * scale
    target = pd.DataFrame({
        "currency": w.index,
        "weight": w.values,
        "rate_pct": rates.loc[today].values,
        "usd_per_unit": fx.loc[today].values,
    })
    target = target[target.weight != 0].sort_values("weight", ascending=False)
    target["side"] = np.where(target.weight > 0, "LONG", "SHORT")
    target["notional_usd"] = (target.weight * config.NOTIONAL_USD).round(0)
    target.to_csv(f"{config.OUTPUT_DIR}/target_trades.csv", index=False)

    print(f"Signal date: {today.date()}   size multiplier: {scale:.2f}")
    if target.empty:
        print("No trade: rate spread below MIN_SPREAD_PCT.")
    else:
        print(target[["currency", "side", "rate_pct", "notional_usd"]].to_string(index=False))
    return target


if __name__ == "__main__":
    main()

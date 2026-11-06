"""STEP 4 - Evaluate the decision.

Backtests the Step 2 rules month by month over the full history and asks:
did the strategy pay, where did the money come from, and how bad were
the crashes?

Outputs:
  output/performance.csv     monthly returns (carry, spot, costs, net)
  output/summary.csv         headline metrics for each variant
  output/performance.png     growth of $1 + drawdown chart

Run:  python step4_evaluate.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from step2_signal import build_weights, currency_returns, load_data, vol_scale


def backtest(fx, rates, use_vol_target=True, cost_bps=config.COST_BPS) -> pd.DataFrame:
    weights = build_weights(fx, rates)
    carry, spot = currency_returns(fx, rates)

    carry_ret = (weights * carry).sum(axis=1)
    spot_ret = (weights * spot).sum(axis=1)
    gross = carry_ret + spot_ret

    scale = vol_scale(gross) if (use_vol_target and config.VOL_TARGET) else pd.Series(1.0, index=gross.index)
    w_scaled = weights.mul(scale, axis=0)
    turnover = w_scaled.diff().abs().sum(axis=1).fillna(w_scaled.abs().sum(axis=1))
    costs = turnover * cost_bps / 10_000

    out = pd.DataFrame({
        "carry": carry_ret * scale,
        "spot": spot_ret * scale,
        "costs": -costs,
    })
    out["net"] = out.sum(axis=1)
    return out.iloc[:-1]                     # last month has no next-month return yet


def metrics(net: pd.Series) -> dict:
    growth = (1 + net).cumprod()
    years = len(net) / 12
    drawdown = growth / growth.cummax() - 1
    vol = net.std() * np.sqrt(12)
    ann = growth.iloc[-1] ** (1 / years) - 1
    return {
        "annual_return_%": round(100 * ann, 2),
        "annual_volatility_%": round(100 * vol, 2),
        "return_per_unit_risk": round(ann / vol, 2) if vol else np.nan,
        "worst_month_%": round(100 * net.min(), 2),
        "worst_month": net.idxmin().strftime("%Y-%m"),
        "max_drawdown_%": round(100 * drawdown.min(), 2),
        "months_traded_%": round(100 * (net != 0).mean(), 1),
    }


def plot(results: dict[str, pd.DataFrame], path: str) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1.3]})
    for name, df in results.items():
        g = (1 + df.net).cumprod()
        ax1.plot(g.index, g, lw=2, label=name)
        ax2.plot(g.index, 100 * (g / g.cummax() - 1), lw=1.5)
    base = next(iter(results.values()))
    ax1.plot(base.index, (1 + base.carry).cumprod(), ls="--", color="gray", lw=1,
             label="interest income only (no FX moves)")
    ax1.set_ylabel("Growth of $1")
    ax1.set_title("Carry trade backtest", loc="left", fontsize=14)
    ax1.legend(frameon=False)
    ax2.set_ylabel("Drawdown %")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main() -> pd.DataFrame:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    fx, rates = load_data()
    results = {
        "rules only": backtest(fx, rates, use_vol_target=False),
        "rules + volatility sizing": backtest(fx, rates, use_vol_target=True),
    }
    summary = pd.DataFrame({k: metrics(v.net) for k, v in results.items()})
    results["rules + volatility sizing"].to_csv(f"{config.OUTPUT_DIR}/performance.csv")
    summary.to_csv(f"{config.OUTPUT_DIR}/summary.csv")
    plot(results, f"{config.OUTPUT_DIR}/performance.png")

    df = results["rules only"]
    print("Where the money came from (rules only, total over the period):")
    print(f"  interest income  {100 * df.carry.sum():7.1f}%")
    print(f"  exchange rates   {100 * df.spot.sum():7.1f}%")
    print(f"  trading costs    {100 * df.costs.sum():7.1f}%")
    print("\nSummary:")
    print(summary.to_string())
    print(f"\nChart saved to {config.OUTPUT_DIR}/performance.png")
    return summary


if __name__ == "__main__":
    main()

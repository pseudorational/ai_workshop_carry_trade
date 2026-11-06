# Carry trade AI workshop: reference pipeline

These four Python steps are the code Claude should generate live in class (see PROMPTS.md):

| File | Step |
| --- | --- |
| `step1_gather.py` | Download FX and interest rates from FRED, normalise quote conventions, save monthly CSVs |
| `step2_signal.py` | Rank by interest rate, go long the top N and short the bottom N, apply a spread filter and volatility sizing |
| `step3_execute.py` | Convert positions to FX orders; paper ledger, or the OANDA practice API |
| `step4_evaluate.py` | Monthly backtest, carry vs FX decomposition, costs, metrics, chart |
| `config.py` | Every rule parameter in one place |
| `run_all.py` | Runs all four steps in order |

## Quick start

```
pip install pandas numpy matplotlib requests
python run_all.py --demo     # offline synthetic data, no internet needed
python run_all.py            # live FRED data
python run_all.py --send     # also "send" orders (paper ledger by default)
```

Outputs go to `data/` and `output/`: target_trades.csv, ledger.csv, summary.csv, performance.png.

Notes:
- `--demo` data is synthetic and only good for testing the plumbing. Don't read anything into its results.
- The OECD interest-rate series are monthly averages, so the signal has a slight timing advantage. Raise this as a discussion point; it's fine for teaching.
- The OANDA broker only works with practice accounts. It reads `OANDA_TOKEN` and `OANDA_ACCOUNT` from the environment.

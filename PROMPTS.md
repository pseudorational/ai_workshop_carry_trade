# Workshop prompts: having Claude write the pipeline

Students watch while you give Claude one prompt per step. Claude writes the Python, you run it, and the class steers by changing the rules in the prompt. The reference code in this folder is what a good answer looks like. Use it to check Claude's output, or as a fallback if a live generation goes sideways.

Start each class in a fresh Claude conversation with code execution turned on.

---

## Prompt 0: Set the context (paste once)

```
We're building a currency carry trade system in Python, one step at a time, in front of a class of undergrad and MBA students from many majors. Write clean, well-commented code that a non-programmer could follow. Keep shared settings (currencies, dates, rule parameters) in a config.py file so the class can change them. Use only pandas, numpy, matplotlib and requests. After writing each file, explain in 3-4 plain-English sentences what it does.
```

---

## Step 1: Gather data

```
Write step1_gather.py. It should download, from FRED (free, no API key, via the fredgraph.csv URL):
- daily spot exchange rates vs the US dollar for EUR, JPY, GBP, CHF, CAD, AUD, NZD, NOK, SEK
- monthly 3-month interbank interest rates (the OECD IR3TIB01 series) for those countries plus the US
from 2005 onward. Convert every exchange rate to "US dollars per 1 unit of foreign currency", resample to month-end, and save fx_monthly.csv and rates_monthly.csv. Print a data-quality report: the last date for each series, and a sanity check showing how many units of each currency one dollar buys.
```

**What to check in Claude's answer**
- Does it notice that FRED quotes some pairs as dollars per foreign unit (DEXUSEU, DEXUSUK, DEXUSAL, DEXUSNZ) and others as foreign units per dollar (DEXJPUS and the rest)? If it doesn't invert the second group, every result downstream comes out backwards for those currencies. This is the best "catch the AI" moment of the session.
- Does it handle FRED's "." missing values?

**Steering options for the class:** a different start date, adding or removing currencies, using the 10-year yield instead of the 3-month rate (and why that would be the wrong choice for carry).

---

## Step 2: Rules that pick the trade

```
Write step2_signal.py. Using the saved data, apply these rules each month:
1. Rank the currencies by interest rate.
2. Go long the [N] highest-rate currencies and short the [N] lowest, equal weights.
3. Skip the trade if the average long rate minus the average short rate is below [X] percentage points.
4. Scale position size so the strategy's volatility is about [Y]% a year, using only PAST data.
Save this month's target positions (currency, long/short, interest rate, dollar notional on a $1,000,000 account) to target_trades.csv and print them.
```

**Class votes:** N = 1 or 3? Minimum spread of 0, 1, or 2 points? Volatility sizing on or off?

**What to check**
- Rule 4 must use `.shift(1)`, or some equivalent, so it never peeks at the current month. Ask Claude directly: "Does any part of this use information we wouldn't have had at the time?"
- Do the weights sum to zero, so the trade is self-funding?

---

## Step 3: Send the trades to a trading system

```
Write step3_execute.py. Read target_trades.csv and convert each currency position into an FX order using OANDA instrument names (e.g. long AUD = buy AUD_USD; long JPY = sell USD_JPY), with units in the base currency. Build two interchangeable brokers:
- PaperBroker: records fills to ledger.csv
- OandaBroker: sends market orders to the OANDA v20 *practice* API (api-fxpractice.oanda.com), reading the token and account ID from environment variables
Default to a dry run that only prints the orders; submit only with a --send flag. Make it impossible to point the code at a live account.
```

**What to check**
- Units: for XXX_USD pairs the units are in the foreign currency, and for USD_XXX pairs they're in dollars. Ask Claude to walk through one order by hand.
- Safety rails: dry run by default, practice URL only, no hard-coded token. This opens the discussion about guardrails on automated agents.

**Optional live demo:** a free OANDA practice account lets the orders actually reach a broker. Set `BROKER = "oanda"` in config.py and export `OANDA_TOKEN` and `OANDA_ACCOUNT` before class.

---

## Step 4: Evaluate the decision

```
Write step4_evaluate.py. Backtest the Step 2 rules month by month from 2005 to today. For each month, split the return into interest income (rate/12) and the exchange-rate move, and subtract a trading cost of [5] basis points per unit of turnover. Report annual return, volatility, return per unit of risk, worst month, and maximum drawdown, comparing the strategy with and without volatility sizing. Save a chart with growth of $1 (plus a dashed line for interest income only) and a drawdown panel underneath.
```

**Discussion prompts**
- The dashed "interest only" line versus the actual line: the gap between them is the exchange-rate risk you're paid to take.
- Which month was worst? Ask Claude: "What happened in markets that month?" (2008, and August 2024 when the yen carry trade unwound.)
- "We picked these rules after seeing the history. Is that cheating?" This is how you introduce overfitting.

---

## Recovery prompts

| Problem | Send |
| --- | --- |
| Code errors | "Here's the error: [paste]. Fix it and explain what was wrong in one sentence." |
| Too much code on screen | "Just show me the function that applies the rules, and explain it line by line." |
| FRED download fails | "The download failed. Run `python step1_gather.py --demo` to use the offline data instead." |
| Results look suspicious | "Sanity-check this: does one dollar really buy [X] [currency]? Check the quote conventions." |

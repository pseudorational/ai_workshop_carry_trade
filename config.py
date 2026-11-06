"""Shared settings for the carry trade workshop pipeline.

Every step imports from here, so students can change one number
(say, how many currencies to go long) and re-run the whole pipeline.
"""

# --- Universe --------------------------------------------------------------
# G10 currencies. USD is the home currency: every exchange rate is
# stored as "US dollars per 1 unit of foreign currency".
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "NOK", "SEK"]

# FRED daily spot exchange rates.
# WARNING (teaching point): FRED quotes these two different ways.
#   "usd_per_fx"  -> already US dollars per foreign unit (e.g. DEXUSEU)
#   "fx_per_usd"  -> foreign units per US dollar (e.g. DEXJPUS) -> must invert
FX_SERIES = {
    "EUR": ("DEXUSEU", "usd_per_fx"),
    "GBP": ("DEXUSUK", "usd_per_fx"),
    "AUD": ("DEXUSAL", "usd_per_fx"),
    "NZD": ("DEXUSNZ", "usd_per_fx"),
    "JPY": ("DEXJPUS", "fx_per_usd"),
    "CAD": ("DEXCAUS", "fx_per_usd"),
    "CHF": ("DEXSZUS", "fx_per_usd"),
    "NOK": ("DEXNOUS", "fx_per_usd"),
    "SEK": ("DEXSDUS", "fx_per_usd"),
}

# FRED monthly 3-month interbank rates (OECD), annual percent.
RATE_SERIES = {
    "USD": "IR3TIB01USM156N",
    "EUR": "IR3TIB01EZM156N",
    "JPY": "IR3TIB01JPM156N",
    "GBP": "IR3TIB01GBM156N",
    "CHF": "IR3TIB01CHM156N",
    "CAD": "IR3TIB01CAM156N",
    "AUD": "IR3TIB01AUM156N",
    "NZD": "IR3TIB01NZM156N",
    "NOK": "IR3TIB01NOM156N",
    "SEK": "IR3TIB01SEM156N",
}

START_DATE = "2005-01-01"
DATA_DIR = "data"
OUTPUT_DIR = "output"

# --- Trading rules (Step 2) -------------------------------------------------
N_LONG = 3              # hold the N highest-rate currencies
N_SHORT = 3             # borrow in the N lowest-rate currencies
MIN_SPREAD_PCT = 1.0    # skip the trade if avg long rate - avg short rate < this
VOL_TARGET = 0.08       # annual volatility target for position sizing (None = off)
VOL_LOOKBACK_MONTHS = 12

# --- Execution (Step 3) -----------------------------------------------------
NOTIONAL_USD = 1_000_000
BROKER = "paper"        # "paper" (local ledger) or "oanda" (OANDA practice account)

# --- Evaluation (Step 4) ----------------------------------------------------
COST_BPS = 5            # trading cost per unit of turnover, in basis points

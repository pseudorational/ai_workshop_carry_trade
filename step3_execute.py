"""STEP 3 - Pass the trades to a trading system.

Turns target positions (per currency vs USD) into FX orders and sends
them to a broker. Two brokers share one interface:

  PaperBroker  -- records fills in output/ledger.csv (default, no account needed)
  OandaBroker  -- sends market orders to an OANDA *practice* account
                  (needs env vars OANDA_TOKEN and OANDA_ACCOUNT)

Safety: orders are only sent when you pass --send. Without it you get a
dry run that prints the orders. The OANDA broker refuses live URLs.

Run:  python step3_execute.py           (dry run)
      python step3_execute.py --send    (submit to the broker in config.BROKER)
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

import config

# Currencies OANDA quotes as XXX_USD; the rest are USD_XXX.
USD_QUOTED = {"EUR", "GBP", "AUD", "NZD"}


def to_orders(target: pd.DataFrame) -> pd.DataFrame:
    """Convert currency weights into instrument + units.

    Long AUD  -> buy  AUD_USD (units in AUD)
    Long JPY  -> sell USD_JPY (units in USD)
    """
    rows = []
    for _, t in target.iterrows():
        ccy, usd = t.currency, t.notional_usd
        if ccy == "USD":
            continue                       # USD legs net out automatically
        if ccy in USD_QUOTED:
            instrument = f"{ccy}_USD"
            units = round(usd / t.usd_per_unit)        # base currency = ccy
        else:
            instrument = f"USD_{ccy}"
            units = round(-usd)                        # base = USD; long ccy = sell USD
        rows.append({"instrument": instrument, "units": int(units),
                     "currency": ccy, "side": t.side, "notional_usd": usd,
                     "ref_price_usd_per_unit": t.usd_per_unit})
    return pd.DataFrame(rows)


class PaperBroker:
    """Simulated broker: fills at the reference price and appends to a ledger."""

    def __init__(self, ledger_path: str = f"{config.OUTPUT_DIR}/ledger.csv"):
        self.ledger_path = ledger_path

    def submit(self, orders: pd.DataFrame) -> pd.DataFrame:
        fills = orders.copy()
        fills["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        fills["status"] = "FILLED (paper)"
        header = not os.path.exists(self.ledger_path)
        fills.to_csv(self.ledger_path, mode="a", header=header, index=False)
        return fills


class OandaBroker:
    """OANDA v20 REST API, practice environment only."""

    BASE_URL = "https://api-fxpractice.oanda.com"

    def __init__(self):
        self.token = os.environ["OANDA_TOKEN"]
        self.account = os.environ["OANDA_ACCOUNT"]
        assert "fxpractice" in self.BASE_URL, "Refusing to trade a live account."

    def submit(self, orders: pd.DataFrame) -> pd.DataFrame:
        url = f"{self.BASE_URL}/v3/accounts/{self.account}/orders"
        headers = {"Authorization": f"Bearer {self.token}",
                   "Content-Type": "application/json"}
        results = []
        for _, o in orders.iterrows():
            body = {"order": {"type": "MARKET", "instrument": o.instrument,
                              "units": str(o.units), "timeInForce": "FOK",
                              "positionFill": "DEFAULT"}}
            r = requests.post(url, json=body, headers=headers, timeout=30)
            ok = r.status_code == 201 and "orderFillTransaction" in r.json()
            results.append({**o.to_dict(), "status": "FILLED" if ok else f"REJECTED {r.status_code}",
                            "response": r.text[:200]})
        return pd.DataFrame(results)


def get_broker():
    return OandaBroker() if config.BROKER == "oanda" else PaperBroker()


def main(send: bool = False) -> pd.DataFrame:
    target = pd.read_csv(f"{config.OUTPUT_DIR}/target_trades.csv")
    orders = to_orders(target)
    print("Orders to send:")
    print(orders[["instrument", "units", "currency", "side", "notional_usd"]].to_string(index=False))
    if not send:
        print("\nDry run only. Re-run with --send to submit to:", config.BROKER)
        return orders
    fills = get_broker().submit(orders)
    print("\nBroker response:")
    print(fills[["instrument", "units", "status"]].to_string(index=False))
    return fills


if __name__ == "__main__":
    main(send="--send" in sys.argv)

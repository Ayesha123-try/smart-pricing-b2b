"""Rule-based price corridor.

For an offer, find similar won deals that closed before the as-of date, starting with the
narrowest comparison group and widening only until there are at least `min_n` deals. Quantiles
of price / list price, multiplied by the offer's list price, give the three corridor prices.
"""
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Narrowest first. The empty last level compares against all products via price / list price,
# so a thinly sold product such as GTK 500 still gets a corridor.
LEVELS = [
    ("product+sector+size", ("product", "sector", "size_band")),
    ("product+sector", ("product", "sector")),
    ("product+size", ("product", "size_band")),
    ("product", ("product",)),
    ("all products", ()),
]
DEFAULT_MIN_N = 30
DEFAULT_QUANTILES = (0.25, 0.50, 0.75)


@dataclass
class Quote:
    conservative: float
    target: float
    stretch: float
    level: str
    n_comparable: int


class PriceCorridor:
    def __init__(self, won, min_n=DEFAULT_MIN_N, quantiles=DEFAULT_QUANTILES, levels=LEVELS):
        self.min_n = min_n
        self.quantiles = quantiles
        self.levels = levels
        self.close_dates = won["close_date"].to_numpy(dtype="datetime64[ns]")
        self.ratios = (won["close_value"] / won["list_price"]).to_numpy(dtype=float)
        self.columns = {c: won[c].to_numpy() for c in ("product", "sector", "size_band")}

    def quote(self, product, sector, size_band, list_price, as_of):
        """Corridor for one offer, using only won deals closed strictly before `as_of`."""
        offer = {"product": product, "sector": sector, "size_band": size_band}
        known = self.close_dates < np.datetime64(as_of, "ns")
        if not known.any():
            return None
        for i, (name, keys) in enumerate(self.levels):
            mask = known.copy()
            for key in keys:
                mask &= self.columns[key] == offer[key]
            n = int(mask.sum())
            if n >= self.min_n or (i == len(self.levels) - 1 and n > 0):
                low, mid, high = np.quantile(self.ratios[mask], self.quantiles)
                return Quote(low * list_price, mid * list_price, high * list_price, name, n)
        return None


def load_deals():
    con = duckdb.connect(str(ROOT / "crm.duckdb"))
    con.execute((ROOT / "sql" / "02_clean.sql").read_text())
    deals = con.execute("SELECT * FROM deals").df()
    con.close()
    for col in ("engage_date", "close_date"):
        deals[col] = pd.to_datetime(deals[col])
    return deals


def quote_book(deals):
    """Latest corridor for every open deal, as a sales team would actually use it."""
    won = deals[deals["deal_stage"] == "Won"]
    corridor = PriceCorridor(won)
    as_of = deals["close_date"].max() + pd.Timedelta(days=1)
    rows = []
    for d in deals[deals["deal_stage"] == "Engaging"].itertuples():
        size = d.size_band if isinstance(d.size_band, str) else None
        sector = d.sector if isinstance(d.sector, str) else None
        q = corridor.quote(d.product, sector, size, d.list_price, as_of)
        rows.append({
            "opportunity_id": d.opportunity_id, "product": d.product, "account": d.account,
            "list_price": d.list_price, "conservative": round(q.conservative, 2),
            "target": round(q.target, 2), "stretch": round(q.stretch, 2),
            "comparison_group": q.level, "n_comparable": q.n_comparable,
        })
    return pd.DataFrame(rows)

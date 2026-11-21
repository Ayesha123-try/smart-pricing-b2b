import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from corridor import PriceCorridor


def won_deals(rows):
    return pd.DataFrame(rows, columns=["product", "sector", "size_band", "close_date", "close_value", "list_price"]).assign(
        close_date=lambda d: pd.to_datetime(d["close_date"]))


def block(n, product="A", sector="retail", size="small", value=100, list_price=100, date="2017-05-01"):
    return [(product, sector, size, date, value, list_price)] * n


def test_uses_narrowest_group_with_enough_deals():
    won = won_deals(block(30, value=90) + block(30, sector="finance", value=110))
    q = PriceCorridor(won, min_n=30).quote("A", "retail", "small", 100, "2017-06-01")
    assert q.level == "product+sector+size"
    assert q.target == pytest.approx(90)
    assert q.n_comparable == 30


def test_widens_only_when_the_narrow_group_is_too_small():
    won = won_deals(block(5, value=90) + block(30, sector="finance", value=110))
    q = PriceCorridor(won, min_n=30).quote("A", "retail", "small", 100, "2017-06-01")
    assert q.level == "product+size"
    assert q.n_comparable == 35


def test_falls_back_to_all_products_using_ratio_to_list():
    won = won_deals(block(30, product="B", value=45, list_price=50))
    q = PriceCorridor(won, min_n=30).quote("A", "retail", "small", 1000, "2017-06-01")
    assert q.level == "all products"
    assert q.target == pytest.approx(900)


def test_future_deals_never_change_the_quote():
    past = block(30, value=90)
    before = PriceCorridor(won_deals(past)).quote("A", "retail", "small", 100, "2017-06-01")
    future = block(500, value=1000, date="2017-07-01")
    after = PriceCorridor(won_deals(past + future)).quote("A", "retail", "small", 100, "2017-06-01")
    assert after == before


def test_deal_closing_on_the_as_of_date_is_not_yet_known():
    won = won_deals(block(30, value=90, date="2017-05-31") + block(30, value=200, date="2017-06-01"))
    q = PriceCorridor(won).quote("A", "retail", "small", 100, "2017-06-01")
    assert q.target == pytest.approx(90)
    assert q.n_comparable == 30


def test_no_history_gives_no_quote():
    won = won_deals(block(30, date="2017-07-01"))
    assert PriceCorridor(won).quote("A", "retail", "small", 100, "2017-06-01") is None


def test_prices_are_ordered():
    rows = [("A", "retail", "small", "2017-05-01", v, 100) for v in range(60, 140)]
    q = PriceCorridor(won_deals(rows)).quote("A", "retail", "small", 100, "2017-06-01")
    assert q.conservative < q.target < q.stretch

import json

import numpy as np
import pandas as pd
import pytest

from swissgrid_cot.annotate import rationales as R
from swissgrid_cot.annotate.anomalies import score_days
from swissgrid_cot.annotate.baseline import daily_frame, fit_baseline
from swissgrid_cot.annotate.causes import attribute, temperature_normal
from swissgrid_cot.annotate.qa import build_window, iso_weeks, window_facts


def _synthetic_hourly(seed: int = 0) -> pd.DataFrame:
    """Two years of hourly data in the shape of ch_hourly.parquet, with a known structure."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-12-31 23:00", "2024-12-31 22:00", freq="h", tz="UTC")
    local = idx.tz_convert("Europe/Zurich")
    date = local.tz_localize(None).normalize()
    doy = local.day_of_year.to_numpy()
    temp = 10 - 10 * np.cos(2 * np.pi * (doy - 15) / 365) + rng.normal(0, 2, len(idx))
    weekend = local.day_of_week >= 5
    load = 6000 + 60 * np.maximum(0, 16 - temp) - 900 * weekend + rng.normal(0, 60, len(idx))
    df = pd.DataFrame(index=idx)
    df["load_enduser_mw"] = load
    df["load_total_mw"] = load + 700
    df["production_mw"] = load + 500
    for b, v in {"at": 100.0, "de": 300.0, "fr": 400.0, "it": -1000.0}.items():
        df[f"net_import_{b}_mw"] = v
    df["net_import_mw"] = -200.0
    df["temp_c"] = temp
    df["radiation_wm2"] = 150.0
    df["local_date"] = date
    df["local_hour"] = local.hour
    df["dow"] = local.day_of_week
    df["holiday_pop_share"] = 0.0
    df["holiday_name"] = None
    df["is_holiday"] = False
    df["is_bridge_day"] = False
    df["year"] = date.year
    return df


@pytest.fixture(scope="module", autouse=True)
def _two_year_splits(monkeypatch_module):
    # The synthetic data spans 2023 (train) and 2024 (test).
    from swissgrid_cot.annotate import baseline as B

    monkeypatch_module.setattr(B, "TRAIN_YEARS", (2023,))
    monkeypatch_module.setattr(B, "VALIDATION_YEARS", ())
    monkeypatch_module.setattr(B, "TEST_YEARS", (2024,))


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_baseline_ignores_test_years():
    """Changing every test-year value must leave the fitted baseline and the residual scale as they are."""
    h = _synthetic_hourly()
    d1 = daily_frame(h)
    h2 = h.copy()
    h2.loc[h2.year == 2024, "load_enduser_mw"] *= 1.5
    h2.loc[h2.year == 2024, "temp_c"] += 7
    d2 = daily_frame(h2)
    b1, b2 = fit_baseline(d1), fit_baseline(d2)
    np.testing.assert_allclose(b1.coef, b2.coef)
    _, s1 = score_days(d1, b1)
    _, s2 = score_days(d2, b2)
    assert s1 == s2
    # The temperature normal is a train-only climatology too.
    np.testing.assert_allclose(temperature_normal(d1).loc["2023"], temperature_normal(d2).loc["2023"])


def test_holiday_dip_is_flagged_and_attributed():
    h = _synthetic_hourly()
    day = h.local_date == pd.Timestamp("2024-05-09")  # a Thursday
    h.loc[day, "load_enduser_mw"] *= 0.75
    h.loc[day, "holiday_pop_share"] = 1.0
    h.loc[day, "holiday_name"] = "Ascension Day"
    h.loc[day, "is_holiday"] = True
    d = daily_frame(h)
    scored, _ = score_days(d, fit_baseline(d))
    a = attribute(scored)
    assert a.loc["2024-05-09", "is_anomaly"]
    assert a.loc["2024-05-09", "cause"] == "public_holiday"
    ordinary = a[(a.index.year == 2024) & ~a.special_day]
    assert ordinary.is_anomaly.mean() < 0.05


def test_windows_are_iso_weeks_with_dst_lengths():
    h = _synthetic_hourly()
    d = daily_frame(h)
    scored, _ = score_days(d, fit_baseline(d))
    scored = attribute(scored)
    scored["weather_effect_mw"] = 0.0
    weeks = iso_weeks(scored)
    assert all(w[0].day_of_week == 0 and len(w) == 7 for w in weeks)
    lengths = {}
    for w in weeks:
        f = window_facts(w, scored, h)
        lengths[f["window_id"]] = f["n_hours"]
    assert lengths["2024-W13"] == 167  # 31 March 2024, spring forward
    assert lengths["2024-W43"] == 169  # 27 October 2024, fall back
    assert lengths["2024-W20"] == 168
    w = build_window(window_facts(weeks[10], scored, h))
    assert w["rationales"]["exchange"].endswith("Answer: net exporter")


def test_number_check_catches_invented_numbers():
    facts = json.dumps({"load": "6,631", "pct": "10.0", "z": "-3.5", "day": "Monday 23 March 2020"})
    ok = "Monday 23 March 2020: 6,631 MW, 10.0% below (z = -3.5) during COVID-19."
    assert R.check_numbers(ok, facts) == set()
    assert R.check_numbers("Monday 23 March 2020: 6,632 MW", facts) == {"6632"}
    assert R.check_numbers("It was 12.5% lower", facts) == {"12.5"}


def test_phrasing_is_deterministic():
    assert R.Phrasing("2024-W13").pick("a", "b", "c") == R.Phrasing("2024-W13").pick("a", "b", "c")

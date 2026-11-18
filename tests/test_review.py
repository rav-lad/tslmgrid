import numpy as np
import pandas as pd
import pytest

from swissgrid_cot.ingest.holdout import partial_labels_to_utc_start
from swissgrid_cot.ingest.swissgrid import SwissgridFormatError, labels_to_utc_start
from swissgrid_cot.review.assess import Calibration, review_day
from swissgrid_cot.review.context import Context
from swissgrid_cot.review.hourly import day_matrix, format_windows, hour_windows
from swissgrid_cot.review.references import Reference
from swissgrid_cot.review.samples import hours_code, parse_answer, parse_hours

FLAT_CAL = Calibration(day_sd={"ordinary": 0.02, "period": 0.04, "holiday": 0.03},
                       hour_sd={g: [0.02] * 24 for g in ("ordinary", "period", "holiday")},
                       n_days={"ordinary": 1, "period": 1, "holiday": 1})  # fmt: skip
SHAPE = 1 + 0.25 * np.sin(np.linspace(0, 2 * np.pi, 24))


def ctx(kind="ordinary", period="regular") -> Context:
    return Context(date=pd.Timestamp("2026-07-01"), weekday="Wednesday", kind=kind, period=period, holiday_name=None,
                   holiday_pop_share=0.0, temp_c=20.0, temp_normal_c=20.0, expected_mw=6000.0, load_mw=6000.0,
                   rel_dev=0.0, z=0.0)  # fmt: skip


def ref(curve, sufficient=True) -> Reference:
    return Reference(curve, [pd.Timestamp("2026-06-24")] * 10, "test days", sufficient, 5)


CANDS = {"weekday": SHAPE, "saturday": SHAPE * 0 + 1, "sunday": 2 - SHAPE}


def test_hour_windows_and_codes_round_trip():
    hours = [0, 1, 2, 7, 8, 23]
    assert hour_windows(hours) == [(0, 2), (7, 8), (23, 23)]
    assert format_windows(hours) == "00:00-02:59, 07:00-08:59, 23:00-23:59"
    assert hours_code(hours) == "00-02,07-08,23-23"
    assert sorted(parse_hours(hours_code(hours))) == hours
    assert hours_code([]) == "none"


def test_parse_answer_reads_the_last_answer_and_the_day_residual():
    text = ("Against the context reference, the day-level residual is +6.7% (z = +3.32). Answer: profile=sunday; "
            "concentrated=morning; outcome=consistent; hours=none. Answer: profile=weekday; concentrated=morning; "
            "outcome=deviation_remains; hours=04-13")  # fmt: skip
    p = parse_answer(text)
    assert p["profile"] == "weekday" and p["outcome"] == "deviation_remains"
    assert p["hours"] == list(range(4, 14))
    assert p["day_residual_pct"] == 6.7
    assert parse_answer("no answer here") is None


def test_identical_curve_is_consistent():
    curve = 6000 * SHAPE
    r = review_day(ctx(), curve.copy(), ref(curve), ref(curve), CANDS, FLAT_CAL)
    assert r.outcome == "consistent" and r.review_hours == []
    assert r.profile == "weekday"


def test_four_hour_step_is_a_remaining_deviation_in_those_hours():
    curve = 6000 * SHAPE
    load = curve.copy()
    load[9:13] *= 0.85
    r = review_day(ctx(), load, ref(curve), ref(curve), CANDS, FLAT_CAL)
    assert r.outcome == "deviation_remains"
    assert r.review_hours == [9, 10, 11, 12]
    assert r.review_mwh < 0
    assert "metering completeness" in r.next_check


def test_two_hour_step_stays_within_tolerance():
    curve = 6000 * SHAPE
    load = curve.copy()
    load[9:11] *= 0.85  # a run shorter than 3 hours does not count
    assert review_day(ctx(), load, ref(curve), ref(curve), CANDS, FLAT_CAL).outcome == "consistent"


def test_whole_day_shift_triggers_on_the_day_level_residual():
    curve = 6000 * SHAPE
    r = review_day(ctx(), curve * 1.10, ref(curve), ref(curve), CANDS, FLAT_CAL)
    assert r.outcome == "deviation_remains"
    assert r.day_residual_pct == pytest.approx(10.0)
    assert len(r.review_hours) == 24


def test_too_few_comparable_days_is_insufficient_evidence():
    curve = 6000 * SHAPE
    r = review_day(ctx(kind="lockdown"), curve, ref(None, sufficient=False), ref(curve), CANDS, FLAT_CAL)
    assert r.outcome == "insufficient_evidence"
    assert r.day_residual_pct is None


def test_day_matrix_fills_spring_forward_and_averages_fall_back():
    rows = []
    for date, hours in (("2026-03-29", [0, 1, 3, *range(4, 24)]), ("2026-10-25", [0, 1, 2, 2, *range(3, 24)])):
        for i, h in enumerate(hours):
            rows.append({"local_date": pd.Timestamp(date), "local_hour": h, "load_enduser_mw": 100.0 + h + (i % 2)})
    m = day_matrix(pd.DataFrame(rows))
    assert m.shape == (2, 24) and not m.isna().any().any()
    spring = m.loc["2026-03-29"]
    assert spring[2] == pytest.approx((spring[1] + spring[3]) / 2)
    assert m.loc["2026-10-25", 2] == pytest.approx(102.5)  # the mean of the two 02:00 hours (102 and 103)


def _labels(start: str, periods: int) -> pd.Series:
    utc = pd.date_range(pd.Timestamp(start).tz_localize("Europe/Zurich").tz_convert("UTC"), periods=periods, freq="15min")
    return pd.Series(utc.tz_convert("Europe/Zurich").tz_localize(None))


def test_current_year_may_stop_at_the_end_of_a_local_day():
    labels = _labels("2026-01-01", 31 * 96)  # January, start labels
    assert len(partial_labels_to_utc_start(labels, 2026)) == 31 * 96
    with pytest.raises(SwissgridFormatError):
        labels_to_utc_start(labels, 2026)  # the main pipeline still requires a complete year
    with pytest.raises(SwissgridFormatError, match="inside a local day"):
        partial_labels_to_utc_start(_labels("2026-01-01", 31 * 96 - 4), 2026)
    shifted = labels.copy()
    shifted.iloc[500] += pd.Timedelta("15min")
    with pytest.raises(SwissgridFormatError, match="row 500"):
        partial_labels_to_utc_start(shifted, 2026)


def test_holdout_split_leaves_2020_2025_splits_alone():
    from swissgrid_cot.review.context import split_with_holdout

    assert [split_with_holdout(y) for y in (2023, 2024, 2025, 2026)] == ["train", "validation", "test", "holdout"]

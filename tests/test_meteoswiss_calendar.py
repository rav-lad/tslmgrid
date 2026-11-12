import numpy as np
import pandas as pd
import pytest

from swissgrid_cot.ingest import meteoswiss
from swissgrid_cot.ingest.calendar_ch import holiday_calendar
from swissgrid_cot.sources import STATION_CANTONS

# Real 2023 BFS figures for a few cantons; the rest get a round number. Only shares matter here.
_POP = pd.Series({c: 100_000 for cs in STATION_CANTONS.values() for c in cs})


def test_station_file_end_labels_become_hour_starts(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        "station_abbr;reference_timestamp;tre200h0;gre000h0\n"
        "SMA;01.01.2020 00:00;-2;0\n"
        "SMA;01.01.2020 01:00;;0\n"
        "SMA;29.03.2020 02:00;3.5;0\n"
    )
    df = meteoswiss.read_station(p, "SMA")
    # UTC throughout: no DST gap on 29 March.
    assert df.index.tolist() == [
        pd.Timestamp("2019-12-31 23:00", tz="UTC"),
        pd.Timestamp("2020-01-01 00:00", tz="UTC"),
        pd.Timestamp("2020-03-29 01:00", tz="UTC"),
    ]
    assert np.isnan(df.temp_c.iloc[1])  # a gap stays a gap
    with pytest.raises(meteoswiss.MeteoSwissFormatError):
        meteoswiss.read_station(p, "GVE")


def test_national_mean_is_weighted_and_needs_coverage():
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    weights = pd.Series({"A": 0.7, "B": 0.2, "C": 0.1})
    st = {
        "A": pd.DataFrame({"temp_c": [10.0, np.nan, 10.0], "radiation_wm2": [0.0, 0.0, 0.0]}, index=idx),
        "B": pd.DataFrame({"temp_c": [0.0, 0.0, np.nan], "radiation_wm2": [0.0, 0.0, 0.0]}, index=idx),
        "C": pd.DataFrame({"temp_c": [0.0, 0.0, 0.0], "radiation_wm2": [0.0, 0.0, 0.0]}, index=idx),
    }
    out = meteoswiss.national_series(st, weights, idx)
    assert out.temp_c.iloc[0] == pytest.approx(7.0)
    assert np.isnan(out.temp_c.iloc[1])  # only 30 % of the weight reports
    assert out.temp_c.iloc[2] == pytest.approx(10.0 * 0.7 / 0.8)  # 80 % reports: renormalised
    assert out.temp_c_coverage.tolist() == pytest.approx([1.0, 0.3, 0.8])


def test_station_weights_sum_to_one_and_cover_every_canton():
    assert sorted(_POP.index) == sorted(
        ["ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL",
         "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "NE", "GE", "JU"]
    )  # fmt: skip
    assert meteoswiss.station_weights(_POP).sum() == pytest.approx(1.0)


def test_holidays_and_bridge_days_2024():
    cal = holiday_calendar("2024-01-01", "2024-12-31", _POP)
    assert cal.loc["2024-08-01", "holiday_pop_share"] == pytest.approx(1.0)
    assert cal.loc["2024-05-09", "is_holiday"]  # Ascension, Thursday
    assert cal.loc["2024-05-10", "is_bridge_day"]  # the Friday after
    assert not cal.loc["2024-05-10", "is_holiday"]
    assert not cal.loc["2024-06-14", "is_holiday"]  # an ordinary Friday
    # 2 January is a holiday only in some cantons, so its share lies strictly between 0 and 1.
    assert 0 < cal.loc["2024-01-02", "holiday_pop_share"] < 1


def test_population_constants_match_the_downloaded_bfs_table():
    from swissgrid_cot.sources import BFS_POPULATION

    if not BFS_POPULATION.path.exists():
        pytest.skip("run sgcot-download first")
    downloaded = meteoswiss.read_canton_population(BFS_POPULATION.path).sort_index()
    pd.testing.assert_series_equal(meteoswiss.canton_population().sort_index(), downloaded, check_names=False)


def test_the_connector_copy_of_the_pipeline_is_up_to_date():
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    if not (repo / "ext" / "TimeNet").exists():
        pytest.skip("the TimeNet checkout is not present")
    done = subprocess.run([sys.executable, str(repo / "scripts" / "sync_connector.py"), "--check"], capture_output=True)
    assert done.returncode == 0, done.stderr.decode()

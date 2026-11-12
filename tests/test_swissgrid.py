from datetime import datetime

import openpyxl
import pandas as pd
import pytest

from swissgrid_cot.ingest import swissgrid
from swissgrid_cot.ingest.swissgrid import SwissgridFormatError, labels_to_utc_start, parse_labels, to_hourly_mw

TZ = "Europe/Zurich"


def _year_starts(year: int) -> pd.DatetimeIndex:
    return pd.date_range(
        pd.Timestamp(year, 1, 1).tz_localize(TZ).tz_convert("UTC"),
        pd.Timestamp(year + 1, 1, 1).tz_localize(TZ).tz_convert("UTC"),
        freq="15min",
        inclusive="left",
    )


def _render(instants: pd.DatetimeIndex, *, fallback_cest: bool = False) -> list[str]:
    """Render UTC instants as Swissgrid labels. ``fallback_cest`` mimics 2020, which writes the
    fall-back instant 01:00 UTC as 03:00 (CEST) instead of 02:00 (CET)."""
    out = []
    for t in instants:
        offset = t.tz_convert(TZ).utcoffset()
        if fallback_cest:
            offset = (t - pd.Timedelta("1us")).tz_convert(TZ).utcoffset()
        out.append((t.tz_localize(None) + offset).strftime("%d.%m.%Y %H:%M"))
    return out


def end_labels(year: int, **kw) -> pd.Series:
    return parse_labels(pd.Series(_render(_year_starts(year) + pd.Timedelta("15min"), **kw)))


def start_labels(year: int) -> pd.Series:
    return parse_labels(pd.Series(_render(_year_starts(year))))


def test_end_labels_map_to_quarter_starts_across_both_dst_changes():
    labels = end_labels(2024)
    # The shape seen in the real 2024 file: spring skips 02:xx, fall repeats 02:00-02:45.
    spring = labels[(labels >= "2024-03-31 01:30") & (labels <= "2024-03-31 03:15")].dt.strftime("%H:%M")
    assert spring.tolist() == ["01:30", "01:45", "03:00", "03:15"]
    fall = labels[(labels.dt.date == pd.Timestamp("2024-10-27").date()) & (labels.dt.hour.between(2, 2))]
    assert fall.dt.strftime("%H:%M").tolist() == ["02:00", "02:15", "02:30", "02:45"] * 2

    idx = labels_to_utc_start(labels, 2024)
    assert idx[0] == pd.Timestamp("2023-12-31 23:00", tz="UTC")
    assert idx[-1] == pd.Timestamp("2024-12-31 22:45", tz="UTC")
    assert (idx.to_series().diff().dropna() == pd.Timedelta("15min")).all()
    # The quarter labelled 03:00 on spring day closes at 01:00 UTC, so it starts at 00:45 UTC.
    pos = labels[labels == pd.Timestamp("2024-03-31 03:00")].index[0]
    assert idx[pos] == pd.Timestamp("2024-03-31 00:45", tz="UTC")


def test_2020_style_fallback_label_is_accepted():
    labels = end_labels(2020, fallback_cest=True)
    day = labels[labels.dt.date == pd.Timestamp("2020-10-25").date()].dt.strftime("%H:%M")
    seq = day[(day >= "02:00") & (day <= "03:00")].tolist()
    assert seq == ["02:00", "02:15", "02:30", "02:45", "03:00", "02:15", "02:30", "02:45", "03:00"]
    assert labels_to_utc_start(labels, 2020).equals(_year_starts(2020).rename("utc_start"))


def test_start_labels_2025():
    labels = start_labels(2025)
    assert labels.iloc[0] == pd.Timestamp("2025-01-01 00:00")
    assert labels.iloc[-1] == pd.Timestamp("2025-12-31 23:45")
    assert labels_to_utc_start(labels, 2025).equals(_year_starts(2025).rename("utc_start"))


def test_end_and_start_conventions_meet_without_overlap():
    a = labels_to_utc_start(end_labels(2024), 2024)
    b = labels_to_utc_start(start_labels(2025), 2025)
    assert b[0] - a[-1] == pd.Timedelta("15min")


@pytest.mark.parametrize("drop", [100, 8650, 28810])  # a plain day, spring day, fall-back day
def test_a_missing_quarter_is_detected(drop):
    labels = end_labels(2024).drop(index=drop).reset_index(drop=True)
    with pytest.raises(SwissgridFormatError, match="rows"):
        labels_to_utc_start(labels, 2024)


def test_a_shifted_row_is_detected():
    labels = end_labels(2024)
    labels = pd.concat([labels.iloc[:500], labels.iloc[501:502], labels.iloc[500:501], labels.iloc[502:]])
    with pytest.raises(SwissgridFormatError, match="row 500"):
        labels_to_utc_start(labels.reset_index(drop=True), 2024)


def test_unknown_first_label_is_rejected():
    labels = end_labels(2024)
    with pytest.raises(SwissgridFormatError, match="neither"):
        labels_to_utc_start(labels.iloc[1:].reset_index(drop=True), 2024)


def test_excel_datetimes_and_strings_parse_alike():
    as_dt = parse_labels(pd.Series([datetime(2020, 1, 1, 0, 15), datetime(2020, 1, 1, 0, 30)]))
    as_str = parse_labels(pd.Series(["01.01.2020 00:15", "01.01.2020 00:30"]))
    assert as_dt.equals(as_str)
    with pytest.raises(SwissgridFormatError, match="grid"):
        parse_labels(pd.Series([datetime(2020, 1, 1, 0, 14)]))


def test_read_year_maps_columns_by_header_not_by_position(tmp_path):
    """Regression: read_excel returns usecols in sheet order, which once swapped production and
    total consumption. Each column here holds its own sheet position, so a swap shows."""
    headers = list(swissgrid.COLUMNS)
    # Put the columns in an order unlike the COLUMNS dict, with a decoy in between.
    order = [headers[2], "Decoy", headers[1], *headers[3:], headers[0]]
    path = tmp_path / "EnergieUebersichtCH-2021.xlsx"
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet(swissgrid.SHEET)
    ws.append([None, *(f"Deutsch\n{h}" for h in order)])
    ws.append(["Zeitstempel", *(["kWh"] * len(order))])
    for label in _render(_year_starts(2021) + pd.Timedelta("15min")):
        ws.append([label, *range(1, len(order) + 1)])
    wb.save(path)

    frame = swissgrid.read_year(path, 2021)
    for position, header in enumerate(order, start=1):
        if header in swissgrid.COLUMNS:
            assert (frame[swissgrid.COLUMNS[header]] == position).all(), header


def test_hourly_aggregation_sums_quarters_and_signs_net_import():
    idx = _year_starts(2024)[:8]
    q = pd.DataFrame({c: 250_000.0 for c in swissgrid.COLUMNS.values()}, index=idx)
    q["imp_de"] = 500_000.0  # 2 MW more import from DE in each hour after summing 4 quarters
    h = to_hourly_mw(q)
    assert len(h) == 2
    assert (h.load_enduser_mw == 1000.0).all()
    assert (h.net_import_de_mw == 1000.0).all()
    assert (h.net_import_mw == 1000.0).all()
    with pytest.raises(SwissgridFormatError, match="four quarters"):
        to_hourly_mw(q.iloc[1:])

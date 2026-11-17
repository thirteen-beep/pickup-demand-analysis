import pandas as pd
import pytest
from demand_analysis import clean_data, analyze


def sample():
    return pd.DataFrame({'Date/Time': ['9/1/2014 08:00:00', '9/1/2014 08:00:00', '9/2/2014 09:00:00'],
                         'Lat': [40.7]*3, 'Lon': [-73.9]*3, 'Base': ['A']*3})


def test_duplicate_rows_preserved():
    clean, audit = clean_data(sample())
    assert len(clean) == 3 and audit['exact_duplicate_rows'] == 1


def test_time_zone_and_sql_equivalence():
    clean, _ = clean_data(sample())
    result = analyze(clean)
    assert str(clean.timestamp.dt.tz) == 'America/New_York'
    assert result['sql_pandas_daily_match']
    assert result['daily'] == [{'day': '2014-09-01', 'pickups': 2}, {'day': '2014-09-02', 'pickups': 1}]


def test_hour_bins_and_absent_weekday():
    clean, _ = clean_data(sample())
    result = analyze(clean)
    assert len(result['hourly']) == 24
    assert result['weekday'][0]['pickups_per_observed_day'] == 2
    assert result['weekday'][6]['pickups_per_observed_day'] is None


def test_weekday_denominator_is_days():
    frame = pd.concat([sample(), sample().assign(**{'Date/Time': '9/8/2014 08:00:00'})])
    clean, _ = clean_data(frame)
    result = analyze(clean)
    assert result['weekday'][0]['observed_days'] == 2
    assert result['weekday'][0]['pickups_per_observed_day'] == 2.5


@pytest.mark.parametrize('column,value,key', [('Date/Time', 'invalid', 'invalid_time'), ('Lat', float('inf'), 'invalid_coordinates'), ('Lat', 30, 'outside_analysis_box')])
def test_invalid_partition(column, value, key):
    frame = sample()
    frame.loc[0, column] = value
    clean, quality = clean_data(frame)
    assert len(clean) == 2 and quality[key] == 1
    assert sum(quality[k] for k in ('retained_rows', 'invalid_time', 'invalid_coordinates', 'outside_analysis_box')) == quality['source_rows']


def test_missing_column():
    with pytest.raises(ValueError):
        clean_data(sample().drop(columns=['Lat']))


def test_empty_observation_window():
    clean, _ = clean_data(sample())
    with pytest.raises(ValueError):
        analyze(clean.iloc[:0])


def test_app_renders():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('streamlit_app.py', default_timeout=45).run()
    assert not app.exception
    assert app.metric[0].label == '接车记录'

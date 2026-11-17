"""Demand analysis of the public September 2014 NYC pickup dataset."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

DATA = Path(__file__).with_name('uber-raw-data-sep14.csv.gz')


def clean_data(frame: pd.DataFrame):
    required = {'Date/Time', 'Lat', 'Lon', 'Base'}
    if not required.issubset(frame.columns):
        raise ValueError('Required columns: Date/Time, Lat, Lon, Base')
    work = frame[list(sorted(required))].copy()
    stamp = pd.to_datetime(work['Date/Time'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
    stamp = stamp.dt.tz_localize('America/New_York', ambiguous='NaT', nonexistent='NaT')
    lat, lon = (pd.to_numeric(work[c], errors='coerce') for c in ('Lat', 'Lon'))
    valid_time = stamp.notna()
    valid_geo = lat.between(-90, 90) & lon.between(-180, 180)
    inside = lat.between(40.0, 41.2) & lon.between(-74.5, -72.5)
    keep = valid_time & valid_geo & inside
    audit = {'source_rows': len(work), 'exact_duplicate_rows': int(work.duplicated().sum()),
             'invalid_time': int((~valid_time).sum()),
             'invalid_coordinates': int((valid_time & ~valid_geo).sum()),
             'outside_analysis_box': int((valid_time & valid_geo & ~inside).sum()),
             'retained_rows': int(keep.sum()),
             'duplicate_policy': 'Retained: no unique trip ID; identical rows are not proven duplicates.'}
    result = pd.DataFrame({'timestamp': stamp[keep], 'lat': lat[keep], 'lon': lon[keep],
                           'base': work.loc[keep, 'Base'].fillna('unknown').astype(str)}).reset_index(drop=True)
    result['day'] = result.timestamp.dt.strftime('%Y-%m-%d')
    result['hour'] = result.timestamp.dt.hour
    result['weekday'] = result.timestamp.dt.dayofweek
    return result, audit


def analyze(frame: pd.DataFrame) -> dict:
    if frame.empty:
        raise ValueError('No records in the selected observation window')
    daily = frame.groupby('day').size().rename('pickups')
    # Independent SQL aggregation checks the pandas result.
    with sqlite3.connect(':memory:') as db:
        frame[['day', 'hour', 'weekday']].to_sql('pickups', db, index=False)
        sql = pd.read_sql_query('SELECT day,COUNT(*) AS pickups FROM pickups GROUP BY day ORDER BY day', db)
    if daily.to_dict() != sql.set_index('day').pickups.to_dict():
        raise ValueError('SQL/Pandas aggregation mismatch')
    hourly = frame.groupby('hour').size().reindex(range(24), fill_value=0)
    day_types = frame[['day', 'weekday']].drop_duplicates()
    observed = day_types.groupby('weekday').size().reindex(range(7), fill_value=0)
    weekday_counts = frame.groupby('weekday').size().reindex(range(7), fill_value=0)
    averages = [round(int(weekday_counts[i])/int(observed[i]), 2) if observed[i] else None for i in range(7)]
    cells = frame.assign(lat_bin=np.floor(frame.lat*100)/100, lon_bin=np.floor(frame.lon*100)/100)
    hotspots = cells.groupby(['lat_bin', 'lon_bin']).size().sort_values(ascending=False).head(10)
    return {
        'rows': len(frame), 'observed_days': len(daily), 'start': daily.index.min(), 'end': daily.index.max(),
        'time_zone': 'America/New_York', 'peak_hour': int(hourly.idxmax()),
        'peak_hour_pickups': int(hourly.max()), 'sql_pandas_daily_match': True,
        'daily': [{'day': day, 'pickups': int(n)} for day, n in daily.items()],
        'hourly': [{'hour': int(h), 'pickups': int(n)} for h, n in hourly.items()],
        'weekday': [{'weekday': i, 'observed_days': int(observed[i]), 'pickups_per_observed_day': averages[i]} for i in range(7)],
        'hotspots': [{'lat_bin': float(lat), 'lon_bin': float(lon), 'pickups': int(n)} for (lat, lon), n in hotspots.items()],
        'limitations': ['Historical public pickup records, not current demand.',
                       'No order IDs, fares, exposure or available-driver counts; no revenue or conversion claims.',
                       'No deduplication without unique trip IDs. Grid counts do not measure unmet demand.',
                       'Weekday rates use observed dates, not an assumption that missing dates had zero rides.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DATA)
    parser.add_argument('--output', type=Path, default=Path('.data/analysis.json'))
    args = parser.parse_args()
    clean, audit = clean_data(pd.read_csv(args.input))
    report = {'quality': audit, 'analysis': analyze(clean)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({**audit, 'peak_hour': report['analysis']['peak_hour'], 'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

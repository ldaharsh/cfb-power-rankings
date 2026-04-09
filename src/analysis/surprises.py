"""Over/under-performing teams per season and all-time."""
import os, csv, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

def load():
    rows = []
    for yr in range(2014, 2026):
        pre = os.path.join(DATA, 'preseason', f'{yr}_preseason.csv')
        sea = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
        if not os.path.exists(pre) or not os.path.exists(sea): continue
        pre_map, n = {}, 0
        with open(pre) as f:
            for r in csv.DictReader(f):
                pre_map[r['team']] = int(r['preseason_rank'])
                n = max(n, int(r['preseason_rank']))
        with open(sea) as f:
            for r in csv.DictReader(f):
                t = r['team']
                if t not in pre_map: continue
                pr, fr = pre_map[t], int(r['final_rank'])
                rows.append({
                    'year': yr, 'team': t,
                    'preseason_rank': pr, 'final_rank': fr,
                    'delta': pr - fr,   # positive = outperformed
                    'n_teams': n,
                })
    return pd.DataFrame(rows)

def by_season(df, yr):
    s = df[df['year'] == yr].copy()
    s = s.sort_values('delta', ascending=False)
    return s[['team','preseason_rank','final_rank','delta']]

def all_time_overperformers(df, min_seasons=3):
    agg = (df.groupby('team')['delta']
             .agg(['mean','count'])
             .rename(columns={'mean':'avg_delta','count':'seasons'})
             .query(f'seasons >= {min_seasons}')
             .sort_values('avg_delta', ascending=False))
    return agg

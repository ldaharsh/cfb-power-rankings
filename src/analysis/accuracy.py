"""Phil Steel preseason accuracy analysis."""
import os, csv, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

def load():
    rows = []
    for yr in range(2014, 2026):
        pre = os.path.join(DATA, 'preseason', f'{yr}_preseason.csv')
        sea = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
        if not os.path.exists(pre) or not os.path.exists(sea): continue
        pre_map = {}
        with open(pre) as f:
            for r in csv.DictReader(f):
                pre_map[r['team']] = int(r['preseason_rank'])
        with open(sea) as f:
            for r in csv.DictReader(f):
                team = r['team']
                if team in pre_map:
                    rows.append({
                        'year': yr, 'team': team,
                        'preseason_rank': pre_map[team],
                        'final_rank': int(r['final_rank']),
                        'delta': pre_map[team] - int(r['final_rank']),  # positive = did better than expected
                    })
    return pd.DataFrame(rows)

def team_accuracy(df):
    """Per-team: avg delta (positive = consistently outperforms Steel)."""
    return (df.groupby('team')['delta']
              .agg(['mean','std','count'])
              .rename(columns={'mean':'avg_delta','std':'std_delta','count':'seasons'})
              .sort_values('avg_delta', ascending=False))

def year_accuracy(df):
    """Per-year: correlation between preseason and final rank."""
    results = []
    for yr, g in df.groupby('year'):
        corr = g['preseason_rank'].corr(g['final_rank'])
        mae = (g['preseason_rank'] - g['final_rank']).abs().mean()
        results.append({'year': yr, 'rank_corr': round(corr, 3), 'mae': round(mae, 1)})
    return pd.DataFrame(results).set_index('year')

def biggest_surprises(df, n=10):
    """Teams with largest single-season outperformance."""
    top = df.nlargest(n, 'delta')[['year','team','preseason_rank','final_rank','delta']]
    bot = df.nsmallest(n, 'delta')[['year','team','preseason_rank','final_rank','delta']]
    return top, bot

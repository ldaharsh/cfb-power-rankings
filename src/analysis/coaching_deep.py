"""Deep coaching analytics: honeymoon effect, recycled coaches, era comparisons."""
import os, csv, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

def load_tenure_df():
    """Build full season-level dataframe with coach tenure year."""
    coaches = []
    with open(os.path.join(DATA, 'coaches.csv')) as f:
        for r in csv.DictReader(f):
            coaches.append(r)

    season_pts = {}
    for yr in range(2014, 2026):
        p = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
        if not os.path.exists(p): continue
        with open(p) as f:
            for r in csv.DictReader(f):
                season_pts[(r['team'], yr)] = int(r['season_points'])

    rows = []
    for c in coaches:
        team, coach = c['team'], c['coach']
        s, e = int(c['start_year']), int(c['end_year'])
        dep = c['departure']
        for yr_idx, yr in enumerate(range(s, e+1), 1):
            pts = season_pts.get((team, yr))
            if pts is None: continue
            rows.append({
                'team': team, 'coach': coach,
                'year': yr, 'tenure_year': yr_idx,
                'tenure_len': e - s + 1,
                'season_points': pts,
                'departure': dep,
            })
    return pd.DataFrame(rows)

def honeymoon_effect(df):
    """Average points by tenure year (year 1, 2, 3, 4, 5+)."""
    df = df.copy()
    df['tenure_bucket'] = df['tenure_year'].clip(upper=6).map(
        lambda x: f'Yr {x}' if x < 6 else 'Yr 6+')
    order = [f'Yr {i}' for i in range(1,6)] + ['Yr 6+']
    agg = (df.groupby('tenure_bucket')['season_points']
             .agg(['mean','count','sem'])
             .reindex(order)
             .rename(columns={'mean':'avg_pts','count':'n','sem':'se'}))
    return agg

def recycled_coaches(df):
    """Coaches who were fired and then hired elsewhere — compare job 1 vs job 2."""
    coaches_raw = []
    with open(os.path.join(DATA, 'coaches.csv')) as f:
        for r in csv.DictReader(f):
            coaches_raw.append(r)

    # Find coaches with multiple stints
    from collections import defaultdict
    stints = defaultdict(list)
    for c in coaches_raw:
        stints[c['coach']].append(c)

    rows = []
    for coach, jobs in stints.items():
        if len(jobs) < 2: continue
        jobs_sorted = sorted(jobs, key=lambda x: int(x['start_year']))
        for i in range(len(jobs_sorted)-1):
            j1, j2 = jobs_sorted[i], jobs_sorted[i+1]
            if j1['departure'] not in ('fired', 'resigned'): continue
            # Get avg points for each stint
            mask1 = (df['coach']==coach) & (df['team']==j1['team'])
            mask2 = (df['coach']==coach) & (df['team']==j2['team'])
            avg1 = df.loc[mask1,'season_points'].mean()
            avg2 = df.loc[mask2,'season_points'].mean()
            if np.isnan(avg1) or np.isnan(avg2): continue
            rows.append({
                'coach': coach,
                'job1_team': j1['team'], 'job1_avg': round(avg1,1),
                'job1_departure': j1['departure'],
                'job2_team': j2['team'], 'job2_avg': round(avg2,1),
                'delta': round(avg2 - avg1, 1),
            })
    return pd.DataFrame(rows).sort_values('delta', ascending=False)

def portal_era_split(df):
    """Compare pre-portal (≤2020) vs portal era (≥2021) for active programs."""
    pre  = df[df['year'] <= 2020].groupby('team')['season_points'].mean()
    post = df[df['year'] >= 2021].groupby('team')['season_points'].mean()
    merged = pd.DataFrame({'pre_avg': pre, 'post_avg': post}).dropna()
    merged['delta'] = merged['post_avg'] - merged['pre_avg']
    return merged.sort_values('delta', ascending=False)

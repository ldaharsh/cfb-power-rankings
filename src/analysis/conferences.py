"""Conference power over time."""
import os, csv, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

MAJOR_CONFS = ['SEC','Big Ten','Big 12','Pac-12','ACC','AAC','Mountain West',
               'C-USA','Sun Belt','MAC','Independent']

def load():
    """Returns merged DataFrame: year, team, conference, season_points, final_rank."""
    conf_map = {}
    with open(os.path.join(DATA, 'conferences.csv')) as f:
        for r in csv.DictReader(f):
            conf_map[(int(r['year']), r['team'])] = r['conference']

    rows = []
    for yr in range(2014, 2026):
        sea = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
        if not os.path.exists(sea): continue
        with open(sea) as f:
            for r in csv.DictReader(f):
                team = r['team']
                conf = conf_map.get((yr, team), 'Unknown')
                rows.append({
                    'year': yr, 'team': team,
                    'conference': conf,
                    'season_points': int(r['season_points']),
                    'final_rank': int(r['final_rank']),
                })
    return pd.DataFrame(rows)

def conf_power_by_year(df, min_teams=4):
    """Average season points per conference per year (Steel-ranked teams only)."""
    # Filter to known conferences and teams with enough company
    known = df[df['conference'] != 'Unknown']
    agg = (known.groupby(['year','conference'])
                .agg(avg_pts=('season_points','mean'),
                     teams=('team','count'),
                     total_pts=('season_points','sum'))
                .reset_index())
    return agg[agg['teams'] >= min_teams]

def top_conf_teams(df, conf, top_n=5):
    """Best teams all-time within a conference."""
    sub = df[df['conference'] == conf]
    return (sub.groupby('team')['season_points']
               .agg(['mean','sum','count'])
               .rename(columns={'mean':'avg_pts','sum':'total_pts','count':'seasons'})
               .sort_values('avg_pts', ascending=False)
               .head(top_n))

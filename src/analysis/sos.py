"""
Strength of Schedule analysis.
For each team/season: average rank of opponents faced (weighted by game).
Also compute SOS-adjusted season points.
"""
import os, csv, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

def load_aliases():
    aliases = {}
    p = os.path.join(DATA, 'team_aliases.csv')
    if os.path.exists(p):
        with open(p) as f:
            for r in csv.DictReader(f):
                aliases[r['cfbd_name'].strip()] = r['steel_name'].strip()
    return aliases

def compute_sos(year):
    """
    Returns DataFrame: team, games_played, avg_opp_rank, sos_percentile
    Lower avg_opp_rank = harder schedule (faced higher-ranked teams).
    """
    aliases = load_aliases()
    game_path = os.path.join(DATA, 'games', f'{year}_games.csv')
    rank_path = os.path.join(DATA, 'rankings', f'{year}_season.csv')
    if not os.path.exists(game_path) or not os.path.exists(rank_path):
        return pd.DataFrame()

    final_ranks = {}
    with open(rank_path) as f:
        for r in csv.DictReader(f):
            final_ranks[r['team']] = int(r['final_rank'])

    team_opps = {}
    with open(game_path) as f:
        for g in csv.DictReader(f):
            home = aliases.get(g['home_team'], g['home_team'])
            away = aliases.get(g['away_team'], g['away_team'])
            for team, opp in [(home, away), (away, home)]:
                opp_rank = final_ranks.get(opp, max(final_ranks.values(), default=200) + 1)
                team_opps.setdefault(team, []).append(opp_rank)

    rows = []
    for team, opp_ranks in team_opps.items():
        if team not in final_ranks: continue
        rows.append({
            'year': year, 'team': team,
            'games': len(opp_ranks),
            'avg_opp_rank': round(np.mean(opp_ranks), 1),
        })
    df = pd.DataFrame(rows)
    if df.empty: return df
    df['sos_pct'] = df['avg_opp_rank'].rank(pct=True)  # higher = easier schedule
    return df.sort_values('avg_opp_rank')

def sos_all_years():
    dfs = [compute_sos(yr) for yr in range(2014, 2026)]
    return pd.concat([d for d in dfs if not d.empty], ignore_index=True)

def hardest_schedules(n=15):
    df = sos_all_years()
    return (df.groupby('team')['avg_opp_rank']
              .mean()
              .sort_values()
              .head(n)
              .rename('avg_opp_rank_alltime'))

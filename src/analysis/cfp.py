"""CFP predictability: how well do our rankings predict playoff participants and champions."""
import os, csv, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# CFP results by season year (games played Jan of year+1)
# 4-team era: 2014-2023.  12-team era: 2024+
CFP = {
    2014: {'champion': 'Ohio St',    'participants': ['Ohio St','Oregon','Alabama','Florida St']},
    2015: {'champion': 'Alabama',    'participants': ['Alabama','Clemson','Michigan St','Oklahoma']},
    2016: {'champion': 'Clemson',    'participants': ['Clemson','Alabama','Ohio St','Washington']},
    2017: {'champion': 'Alabama',    'participants': ['Alabama','Georgia','Ohio St','Clemson']},
    2018: {'champion': 'Clemson',    'participants': ['Clemson','Alabama','Notre Dame','Oklahoma']},
    2019: {'champion': 'LSU',        'participants': ['LSU','Ohio St','Clemson','Oklahoma']},
    2020: {'champion': 'Alabama',    'participants': ['Alabama','Ohio St','Clemson','Notre Dame']},
    2021: {'champion': 'Georgia',    'participants': ['Georgia','Alabama','Michigan','Cincinnati']},
    2022: {'champion': 'Georgia',    'participants': ['Georgia','Ohio St','TCU','Michigan']},
    2023: {'champion': 'Michigan',   'participants': ['Michigan','Washington','Texas','Alabama']},
    2024: {'champion': 'Ohio St',    'participants': ['Ohio St','Notre Dame','Penn St','Texas',
                                                       'Oregon','Indiana','Boise St','SMU',
                                                       'Clemson','Tennessee','Arizona St','Georgia']},
}

def load_season_ranks(yr):
    p = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
    if not os.path.exists(p): return {}
    ranks = {}
    with open(p) as f:
        for r in csv.DictReader(f):
            ranks[r['team']] = int(r['final_rank'])
    return ranks

def cfp_prediction_table():
    rows = []
    for yr, info in CFP.items():
        ranks = load_season_ranks(yr)
        if not ranks: continue
        champ = info['champion']
        parts = info['participants']
        champ_rank = ranks.get(champ, None)
        part_ranks = sorted([ranks.get(t, 999) for t in parts])
        our_top4 = sorted(ranks.items(), key=lambda x: x[1])[:4]
        our_top12 = sorted(ranks.items(), key=lambda x: x[1])[:12]
        our_top4_teams = [t for t,_ in our_top4]
        our_top12_teams = [t for t,_ in our_top12]
        overlap4 = len(set(our_top4_teams) & set(parts[:4]))
        overlap12 = len(set(our_top12_teams) & set(parts))
        rows.append({
            'year': yr,
            'champion': champ,
            'our_champ_rank': champ_rank,
            'cfp_teams': len(parts),
            'top4_overlap': overlap4,
            'top12_overlap': min(overlap12, len(parts)),
            'champ_in_our_top4': champ in our_top4_teams,
            'champ_in_our_top12': champ in our_top12_teams,
        })
    return pd.DataFrame(rows).set_index('year')

def weekly_rank_of_champion():
    """Track how early in each season the eventual champion reached #1 in our rankings."""
    results = []
    for yr, info in CFP.items():
        champ = info['champion']
        wp = os.path.join(DATA, 'rankings', f'{yr}_weekly.csv')
        if not os.path.exists(wp): continue
        with open(wp) as f:
            rows = list(csv.DictReader(f))
        weeks = sorted(set(r['week'] for r in rows))
        first_top3 = None
        for wk in weeks:
            wk_data = {r['team']: int(r['rank']) for r in rows if r['week']==wk}
            cr = wk_data.get(champ, 999)
            if cr <= 3 and first_top3 is None:
                first_top3 = wk
        results.append({'year': yr, 'champion': champ,
                        'first_top3_week': first_top3,
                        'total_weeks': len(weeks)})
    return pd.DataFrame(results).set_index('year')

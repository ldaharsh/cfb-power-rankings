"""
Identify CFBD team names that don't match any Phil Steel team name.
These teams will be treated as 'unranked' when they should be ranked.
"""

import os
import csv
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PRESEASON_DIR = os.path.join(DATA_DIR, 'preseason')
GAMES_DIR = os.path.join(DATA_DIR, 'games')


def load_steel_names():
    names = set()
    for fname in os.listdir(PRESEASON_DIR):
        if not fname.endswith('.csv'):
            continue
        with open(os.path.join(PRESEASON_DIR, fname)) as f:
            for row in csv.DictReader(f):
                names.add(row['team'])
    return names


def load_aliases():
    aliases = {}
    alias_path = os.path.join(DATA_DIR, 'team_aliases.csv')
    if os.path.exists(alias_path):
        with open(alias_path) as f:
            for row in csv.DictReader(f):
                aliases[row['cfbd_name'].strip()] = row['steel_name'].strip()
    return aliases


def load_cfbd_names():
    """All unique team names that appear in game files."""
    names = defaultdict(set)  # cfbd_name -> set of years seen
    for fname in os.listdir(GAMES_DIR):
        if not fname.endswith('.csv'):
            continue
        year = fname[:4]
        with open(os.path.join(GAMES_DIR, fname)) as f:
            for row in csv.DictReader(f):
                names[row['home_team']].add(year)
                names[row['away_team']].add(year)
    return names


def diagnose():
    steel_names = load_steel_names()
    aliases = load_aliases()
    cfbd_names = load_cfbd_names()

    print(f'Phil Steel unique team names: {len(steel_names)}')
    print(f'CFBD unique team names: {len(cfbd_names)}')
    print(f'Aliases defined: {len(aliases)}')
    print()

    unmatched = []
    for cfbd_name, years in sorted(cfbd_names.items()):
        resolved = aliases.get(cfbd_name, cfbd_name)
        if resolved not in steel_names:
            unmatched.append((cfbd_name, resolved, sorted(years)))

    print(f'CFBD names with no Steel match ({len(unmatched)} teams):')
    print(f'  {"CFBD Name":<35} {"Resolved As":<35} Years')
    print(f'  {"-"*35} {"-"*35} -----')
    for cfbd_name, resolved, years in unmatched:
        yrs = ','.join(y[-2:] for y in years)
        print(f'  {cfbd_name:<35} {resolved:<35} {yrs}')


if __name__ == '__main__':
    diagnose()

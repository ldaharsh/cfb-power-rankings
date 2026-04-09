"""
Fetch college football game results from the College Football Data API (CFBD).
Requires a free API key from https://collegefootballdata.com/key

Set environment variable: CFBD_API_KEY=your_key
Or pass --key YOUR_KEY on the command line.

Outputs: data/games/{year}_games.csv
Columns: date, home_team, away_team, home_score, away_score
"""

import os
import csv
import sys
import time
import argparse
import requests
from datetime import datetime, timezone

GAMES_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'games')
BASE_URL = 'https://api.collegefootballdata.com'
YEARS = list(range(2014, 2026))


def fetch_games_for_year(year, api_key, debug=False):
    headers = {'Authorization': f'Bearer {api_key}'}
    all_games = []

    for season_type in ('regular', 'postseason'):
        url = f'{BASE_URL}/games'
        # Try with classification=fbs first (newer API), fall back to division=fbs
        for fbs_param in ({'classification': 'fbs'}, {'division': 'fbs'}, {}):
            params = {'year': year, 'seasonType': season_type, **fbs_param}
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 401:
                print('ERROR: Invalid or missing API key. Get a free key at https://collegefootballdata.com/key')
                sys.exit(1)
            resp.raise_for_status()
            games = resp.json()
            if debug and not all_games and games:
                print(f'  DEBUG sample game keys: {list(games[0].keys())}')
                print(f'  DEBUG sample game: {games[0]}')
            if games:
                all_games.extend(games)
                break  # found data with this param set
            time.sleep(0.2)
        time.sleep(0.3)

    return all_games


def parse_game_date(start_date_str):
    """Extract YYYY-MM-DD from ISO 8601 string."""
    try:
        dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return start_date_str[:10] if start_date_str else ''


def save_games(year, games):
    os.makedirs(GAMES_DIR, exist_ok=True)
    out_path = os.path.join(GAMES_DIR, f'{year}_games.csv')

    rows = []
    for g in games:
        home = g.get('homeTeam', '')
        away = g.get('awayTeam', '')
        home_pts = g.get('homePoints')
        away_pts = g.get('awayPoints')
        date = parse_game_date(g.get('startDate', ''))

        # Skip games with no score (cancelled / not yet played)
        if home_pts is None or away_pts is None:
            continue
        if not home or not away:
            continue

        rows.append({
            'date': date,
            'home_team': home,
            'away_team': away,
            'home_score': int(home_pts),
            'away_score': int(away_pts),
        })

    # Sort by date
    rows.sort(key=lambda r: r['date'])

    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'home_team', 'away_team', 'home_score', 'away_score'])
        writer.writeheader()
        writer.writerows(rows)

    return out_path, len(rows)


def fetch_all(api_key, years=None, debug=False):
    if years is None:
        years = YEARS
    for year in years:
        print(f'Fetching {year}...', end=' ', flush=True)
        games = fetch_games_for_year(year, api_key, debug=debug)
        path, count = save_games(year, games)
        print(f'{count} games -> {os.path.basename(path)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch CFBD game data')
    parser.add_argument('--key', help='CFBD API key (or set CFBD_API_KEY env var)')
    parser.add_argument('--years', nargs='+', type=int, help='Specific years to fetch')
    parser.add_argument('--debug', action='store_true', help='Print raw API response for first game')
    args = parser.parse_args()

    api_key = args.key or os.environ.get('CFBD_API_KEY', '')
    if not api_key:
        print('ERROR: Provide API key via --key or CFBD_API_KEY environment variable.')
        print('Get a free key at: https://collegefootballdata.com/key')
        sys.exit(1)

    fetch_all(api_key, args.years, debug=args.debug)

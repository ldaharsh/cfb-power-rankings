"""
Ranking engine.

Algorithm:
- N = number of teams in Phil Steel's preseason rankings for that year
- Initialization: team ranked #k (1=best) starts with (N+1-k) points
  - Ties in preseason rank (same start_rating): share worst position (highest k)
- Win vs team currently ranked R: +(N+1-R) points
- Loss vs team currently ranked R: -R points
- Win vs unranked team: +1 point
- Loss vs unranked team: -N points
- Re-rank at end of each game day by cumulative points descending
  - Ties in points share worst (highest-numbered) rank of tied group

Multi-year (program) ranking:
- Each season ends with final season-end point totals
- All-time = sum of season-end point totals across all seasons played
"""

import os
import csv
from collections import defaultdict


PRESEASON_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'preseason')
GAMES_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'games')
RANKINGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'rankings')

# Team name aliases: maps CFBD name -> Phil Steel name
# Populated from team_aliases.csv if it exists
_ALIASES = None


def load_aliases():
    global _ALIASES
    if _ALIASES is not None:
        return _ALIASES
    _ALIASES = {}
    alias_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'team_aliases.csv')
    if os.path.exists(alias_path):
        with open(alias_path) as f:
            for row in csv.DictReader(f):
                _ALIASES[row['cfbd_name'].strip()] = row['steel_name'].strip()
    return _ALIASES


def normalize_name(name, aliases=None):
    if aliases is None:
        aliases = load_aliases()
    return aliases.get(name, name)


def load_preseason(year):
    """Returns list of (team, preseason_rank) sorted by preseason_rank ascending."""
    path = os.path.join(PRESEASON_DIR, f'{year}_preseason.csv')
    if not os.path.exists(path):
        return []
    teams = []
    with open(path) as f:
        for row in csv.DictReader(f):
            teams.append((row['team'], int(row['preseason_rank'])))
    teams.sort(key=lambda x: x[1])
    return teams


def load_games(year):
    """Returns list of game dicts sorted by date."""
    path = os.path.join(GAMES_DIR, f'{year}_games.csv')
    if not os.path.exists(path):
        return []
    games = []
    with open(path) as f:
        for row in csv.DictReader(f):
            games.append({
                'date': row['date'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'home_score': int(row['home_score']),
                'away_score': int(row['away_score']),
            })
    games.sort(key=lambda g: g['date'])
    return games


def assign_ranks(points_dict):
    """
    Given {team: points}, return {team: rank} where rank is 1-based,
    ties share the worst (highest-numbered) rank of their group.
    E.g., if 3 teams tie for positions 2,3,4 they all get rank 4.
    """
    sorted_teams = sorted(points_dict.items(), key=lambda x: x[1], reverse=True)
    n = len(sorted_teams)
    ranks = {}
    i = 0
    while i < n:
        j = i
        pts = sorted_teams[i][1]
        while j < n and sorted_teams[j][1] == pts:
            j += 1
        # All teams in [i,j) have the same points; assign rank = j (worst in group)
        for k in range(i, j):
            ranks[sorted_teams[k][0]] = j
        i = j
    return ranks


def run_season(year):
    """
    Run the ranking algorithm for a single season.
    Returns:
        season_end_points: {team: final_season_points}
        daily_snapshots: list of (date, {team: rank}) for each game day
    """
    aliases = load_aliases()
    preseason = load_preseason(year)
    if not preseason:
        print(f'  No preseason data for {year}')
        return {}, []

    n = len(preseason)
    steel_teams = set(team for team, _ in preseason)

    # Initialize points: rank k -> (n+1-k) points
    points = {}
    for team, rank in preseason:
        points[team] = n + 1 - rank

    # Build initial ranked set — only Steel-ranked FBS teams are ever ranked
    current_ranks = assign_ranks({t: p for t, p in points.items() if t in steel_teams})

    games = load_games(year)
    if not games:
        print(f'  No game data for {year} - returning preseason standings')
        return dict(points), []

    # Group games by date
    games_by_date = defaultdict(list)
    for g in games:
        games_by_date[g['date']].append(g)

    daily_snapshots = []

    for date in sorted(games_by_date.keys()):
        day_games = games_by_date[date]

        for g in day_games:
            home = normalize_name(g['home_team'], aliases)
            away = normalize_name(g['away_team'], aliases)
            home_score = g['home_score']
            away_score = g['away_score']

            if home_score == away_score:
                # Tie: no points awarded (very rare in college football)
                continue

            if home_score > away_score:
                winner, loser = home, away
            else:
                winner, loser = away, home

            # Get opponent's current rank for point calculation
            # Use rank AT START of this game day (current_ranks from end of previous day)
            loser_rank = current_ranks.get(loser)
            winner_rank = current_ranks.get(winner)

            # Points for winner
            if loser_rank is not None:
                win_pts = n + 1 - loser_rank
            else:
                win_pts = 1  # unranked opponent

            # Points lost by loser
            if winner_rank is not None:
                loss_pts = winner_rank
            else:
                loss_pts = n  # lost to unranked: max penalty

            # Apply points - initialize unranked teams at 0 if not yet seen
            if winner not in points:
                points[winner] = 0
            if loser not in points:
                points[loser] = 0

            points[winner] += win_pts
            points[loser] -= loss_pts

        # Re-rank after all games on this day are processed — Steel teams only
        current_ranks = assign_ranks({t: p for t, p in points.items() if t in steel_teams})
        daily_snapshots.append((date, dict(current_ranks)))

    return dict(points), daily_snapshots


def save_weekly_snapshots(year, daily_snapshots, season_end_points):
    """Save one ranking snapshot per week (last game-day of each ISO week)."""
    if not daily_snapshots:
        return
    from datetime import date as date_cls
    os.makedirs(RANKINGS_DIR, exist_ok=True)
    out_path = os.path.join(RANKINGS_DIR, f'{year}_weekly.csv')

    # Group snapshots by ISO week, keep last day of each week
    from collections import OrderedDict
    weeks = OrderedDict()
    for date_str, ranks in daily_snapshots:
        try:
            d = date_cls.fromisoformat(date_str)
            wk = f'{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}'
            weeks[wk] = (date_str, ranks)
        except Exception:
            pass

    # Also grab the cumulative points for each snapshot week
    # We need points, not just ranks – re-derive from the final ranks won't work,
    # so we store ranks only (sufficient for trend analysis)
    # Only keep Steel-ranked FBS teams
    preseason_path = os.path.join(PRESEASON_DIR, f'{year}_preseason.csv')
    steel_teams = set()
    if os.path.exists(preseason_path):
        with open(preseason_path) as f:
            for row in csv.DictReader(f):
                steel_teams.add(row['team'])

    rows = []
    for wk, (date_str, ranks) in weeks.items():
        for team, rank in ranks.items():
            if team not in steel_teams:
                continue
            rows.append({'year': year, 'week': wk, 'date': date_str,
                         'team': team, 'rank': rank})

    with open(out_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['year','week','date','team','rank'])
        w.writeheader(); w.writerows(rows)


def save_season_rankings(year, season_end_points, preseason):
    os.makedirs(RANKINGS_DIR, exist_ok=True)
    n = len(preseason)

    # Build preseason rank lookup
    preseason_rank_map = {team: rank for team, rank in preseason}
    steel_teams = set(preseason_rank_map.keys())

    # Only rank Steel-listed FBS teams
    fbs_points = {t: p for t, p in season_end_points.items() if t in steel_teams}

    # Compute final ranks among FBS teams only
    final_ranks = assign_ranks(fbs_points)

    rows = []
    for team, pts in sorted(fbs_points.items(), key=lambda x: x[1], reverse=True):
        rows.append({
            'team': team,
            'final_rank': final_ranks[team],
            'season_points': pts,
            'preseason_rank': preseason_rank_map.get(team, 'NR'),
        })

    out_path = os.path.join(RANKINGS_DIR, f'{year}_season.csv')
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['team', 'final_rank', 'season_points', 'preseason_rank'])
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def load_all_steel_names():
    """Return set of all team names that appear in any Phil Steel preseason file."""
    names = set()
    for fname in os.listdir(PRESEASON_DIR):
        if not fname.endswith('.csv'):
            continue
        with open(os.path.join(PRESEASON_DIR, fname)) as f:
            for row in csv.DictReader(f):
                names.add(row['team'])
    return names


def run_all_seasons(years=None):
    if years is None:
        years = list(range(2014, 2026))

    alltime_points = defaultdict(int)  # team -> sum of season-end points
    steel_names = load_all_steel_names()  # only accumulate Steel-ranked programs

    for year in years:
        games_path = os.path.join(GAMES_DIR, f'{year}_games.csv')
        if not os.path.exists(games_path):
            print(f'{year}: no game data (run fetch_games.py first)')
            continue

        print(f'Running {year}...', end=' ', flush=True)
        season_end_points, snapshots = run_season(year)
        preseason = load_preseason(year)

        path = save_season_rankings(year, season_end_points, preseason)
        save_weekly_snapshots(year, snapshots, season_end_points)
        print(f'{len(season_end_points)} teams, {len(snapshots)} game days -> {os.path.basename(path)}')

        for team, pts in season_end_points.items():
            if team in steel_names:
                alltime_points[team] += pts

    # Save all-time rankings
    save_alltime_rankings(alltime_points)
    return alltime_points


def save_alltime_rankings(alltime_points):
    os.makedirs(RANKINGS_DIR, exist_ok=True)
    alltime_ranks = assign_ranks(alltime_points)

    rows = sorted(alltime_points.items(), key=lambda x: x[1], reverse=True)
    out_path = os.path.join(RANKINGS_DIR, 'alltime.csv')
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['rank', 'team', 'total_points'])
        writer.writeheader()
        for team, pts in rows:
            writer.writerow({'rank': alltime_ranks[team], 'team': team, 'total_points': pts})

    return out_path


if __name__ == '__main__':
    run_all_seasons()

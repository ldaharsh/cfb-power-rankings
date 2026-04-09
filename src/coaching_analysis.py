"""
Coaching staff analysis:
- Points and rank per coach per team
- Trending teams (based on last 3 seasons vs prior)
- Fired coach performance profile
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
RANKINGS_DIR = os.path.join(DATA_DIR, 'rankings')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..')

YEARS = list(range(2014, 2026))


# ── data loaders ──────────────────────────────────────────────────────────────

def load_coaches():
    """Returns list of dicts: team, coach, start_year, end_year, departure"""
    path = os.path.join(DATA_DIR, 'coaches.csv')
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({
                'team': r['team'],
                'coach': r['coach'],
                'start_year': int(r['start_year']),
                'end_year': int(r['end_year']),
                'departure': r['departure'],
            })
    return rows


def load_all_season_points():
    """Returns {team: {year: {points, rank}}}"""
    data = defaultdict(dict)
    for year in YEARS:
        path = os.path.join(RANKINGS_DIR, f'{year}_season.csv')
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for row in csv.DictReader(f):
                data[row['team']][year] = {
                    'points': int(row['season_points']),
                    'rank': int(row['final_rank']),
                }
    return data


def get_coach_for_team_year(coaches, team, year):
    for c in coaches:
        if c['team'] == team and c['start_year'] <= year <= c['end_year']:
            return c['coach']
    return None


# ── trend analysis ────────────────────────────────────────────────────────────

def compute_trends(season_data, coaches, recent_n=3):
    """
    For each Steel-tracked team, compute trend score.
    trend = avg points in last N seasons minus avg points in prior seasons.
    Also compute linear slope across all seasons for a simpler signal.
    Returns list of (team, trend_score, slope, recent_avg, prior_avg, current_coach)
    sorted by trend_score descending.
    """
    results = []
    all_coaches = {(c['team'], yr): c['coach']
                   for c in coaches
                   for yr in range(c['start_year'], c['end_year'] + 1)}

    for team, yearly in season_data.items():
        yr_sorted = sorted(yearly.keys())
        if len(yr_sorted) < 4:
            continue
        pts = [yearly[y]['points'] for y in yr_sorted]
        recent = pts[-recent_n:]
        prior = pts[:-recent_n]
        recent_avg = np.mean(recent)
        prior_avg = np.mean(prior) if prior else recent_avg
        trend_score = recent_avg - prior_avg

        # Linear slope across all seasons
        x = np.arange(len(pts))
        slope = np.polyfit(x, pts, 1)[0]

        current_coach = all_coaches.get((team, max(yr_sorted)), 'Unknown')
        results.append((team, trend_score, slope, recent_avg, prior_avg, current_coach))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ── coach tenure stats ────────────────────────────────────────────────────────

def coach_tenure_stats(coaches, season_data):
    """
    For each coach tenure, compute avg points, avg rank, point trend within tenure,
    and seasons coached.
    Returns list of dicts.
    """
    rows = []
    for c in coaches:
        team = c['team']
        if team not in season_data:
            continue
        tenure_years = [y for y in range(c['start_year'], c['end_year'] + 1)
                        if y in season_data[team]]
        if not tenure_years:
            continue
        pts_list = [season_data[team][y]['points'] for y in tenure_years]
        rank_list = [season_data[team][y]['rank'] for y in tenure_years]
        n = len(tenure_years)
        avg_pts = np.mean(pts_list)
        avg_rank = np.mean(rank_list)

        # Internal trend (slope within tenure)
        if n >= 2:
            slope = np.polyfit(range(n), pts_list, 1)[0]
        else:
            slope = 0.0

        rows.append({
            'team': team,
            'coach': c['coach'],
            'start_year': c['start_year'],
            'end_year': c['end_year'],
            'seasons': n,
            'departure': c['departure'],
            'avg_points': round(avg_pts, 1),
            'avg_rank': round(avg_rank, 1),
            'slope': round(slope, 1),
            'first_season_pts': pts_list[0],
            'last_season_pts': pts_list[-1],
            'pts_list': pts_list,
        })
    return rows


# ── plots ─────────────────────────────────────────────────────────────────────

def plot_trending_teams(trends, top_n=20):
    top = trends[:top_n]
    teams = [t[0] for t in top]
    scores = [t[1] for t in top]
    coaches = [t[5] for t in top]
    recent = [t[3] for t in top]
    prior = [t[4] for t in top]

    fig, ax = plt.subplots(figsize=(13, 8))
    x = np.arange(len(teams))
    width = 0.35

    bars1 = ax.bar(x - width/2, prior, width, label='Prior avg (before last 3 seasons)',
                   color='#aec6e8', edgecolor='white')
    bars2 = ax.bar(x + width/2, recent, width, label='Recent avg (last 3 seasons)',
                   color='#2171b5', edgecolor='white')

    ax.axhline(0, color='black', linewidth=0.7, linestyle='--', alpha=0.4)
    ax.set_title(f'Top {top_n} Trending Up Teams — Recent vs Prior Avg Season Points',
                 fontsize=13, fontweight='bold')
    ax.set_ylabel('Avg Season Points')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{t}\n({c})' for t, c in zip(teams, coaches)],
                       rotation=45, ha='right', fontsize=8)
    ax.legend()

    # Annotate trend delta
    for xi, sc in zip(x, scores):
        ax.annotate(f'{sc:+.0f}', xy=(xi, max(prior[x.tolist().index(xi)],
                                               recent[x.tolist().index(xi)]) + 5),
                    ha='center', fontsize=7, color='#d62728', fontweight='bold')

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'trending_up.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved: {out}')


def plot_fired_coach_profiles(tenure_stats):
    """
    Show the point trajectory for coaches who were fired,
    grouped by how their performance looked in their final 2 seasons.
    """
    fired = [r for r in tenure_stats if r['departure'] == 'fired' and r['seasons'] >= 2]

    # Sort by slope ascending (most declining first)
    fired.sort(key=lambda x: x['slope'])

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Fired Coaches — Performance Profile', fontsize=13, fontweight='bold')

    # Left: avg points distribution for fired vs non-fired
    not_fired = [r for r in tenure_stats if r['departure'] != 'fired' and r['departure'] != 'active']
    active = [r for r in tenure_stats if r['departure'] == 'active']

    ax = axes[0]
    bins = np.linspace(-400, 1200, 30)
    ax.hist([r['avg_points'] for r in fired], bins=bins, alpha=0.7,
            label=f'Fired ({len(fired)})', color='#d62728')
    ax.hist([r['avg_points'] for r in not_fired], bins=bins, alpha=0.7,
            label=f'Left voluntarily ({len(not_fired)})', color='#2171b5')
    ax.hist([r['avg_points'] for r in active], bins=bins, alpha=0.5,
            label=f'Active ({len(active)})', color='#2ca02c')
    ax.axvline(np.mean([r['avg_points'] for r in fired]), color='#d62728',
               linestyle='--', linewidth=1.5, label=f'Fired avg: {np.mean([r["avg_points"] for r in fired]):.0f}')
    ax.axvline(np.mean([r['avg_points'] for r in not_fired]), color='#2171b5',
               linestyle='--', linewidth=1.5, label=f'Left avg: {np.mean([r["avg_points"] for r in not_fired]):.0f}')
    ax.set_title('Avg Season Points by Departure Type')
    ax.set_xlabel('Avg Season Points')
    ax.set_ylabel('# Coach Tenures')
    ax.legend(fontsize=7)

    # Right: scatter — avg_points vs slope, colored by departure
    ax2 = axes[1]
    for r in not_fired:
        ax2.scatter(r['avg_points'], r['slope'], color='#2171b5', alpha=0.5, s=30)
    for r in active:
        ax2.scatter(r['avg_points'], r['slope'], color='#2ca02c', alpha=0.5, s=30)
    for r in fired:
        ax2.scatter(r['avg_points'], r['slope'], color='#d62728', alpha=0.7, s=40)
        if r['avg_points'] < 100 or r['slope'] < -100:
            ax2.annotate(f"{r['coach'][:12]}\n({r['team'][:8]})",
                         (r['avg_points'], r['slope']),
                         fontsize=6, xytext=(4, 4), textcoords='offset points')

    ax2.axhline(0, color='black', linewidth=0.7, linestyle='--', alpha=0.4)
    ax2.axvline(0, color='black', linewidth=0.7, linestyle='--', alpha=0.4)
    ax2.set_title('Avg Points vs In-Tenure Trend Slope')
    ax2.set_xlabel('Avg Season Points')
    ax2.set_ylabel('Point slope per season (within tenure)')

    patches = [
        mpatches.Patch(color='#d62728', label='Fired'),
        mpatches.Patch(color='#2171b5', label='Left voluntarily'),
        mpatches.Patch(color='#2ca02c', label='Active'),
    ]
    ax2.legend(handles=patches, fontsize=8)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, 'fired_coach_profiles.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved: {out}')


def plot_team_with_coaches(team, season_data, coaches):
    """Enhanced version of plot_team with coach data from the coaches DB."""
    if team not in season_data:
        print(f'No data for {team}')
        return

    team_coaches = sorted([c for c in coaches if c['team'] == team],
                          key=lambda x: x['start_year'])

    yearly = season_data[team]
    years = sorted(yearly.keys())
    points = [yearly[y]['points'] for y in years]
    ranks = [yearly[y]['rank'] for y in years]

    # Map year -> coach
    yr_coach = {}
    for c in team_coaches:
        for y in range(c['start_year'], c['end_year'] + 1):
            yr_coach[y] = (c['coach'], c['departure'])

    seen_coaches = []
    coach_seq = []
    for y in years:
        name, dep = yr_coach.get(y, ('Unknown', 'unknown'))
        coach_seq.append((name, dep))
        if name not in [x[0] for x in seen_coaches]:
            seen_coaches.append((name, dep))

    COLORS = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3',
              '#ff7f00', '#a65628', '#f781bf', '#555555']
    color_map = {c[0]: COLORS[i % len(COLORS)] for i, c in enumerate(seen_coaches)}
    bar_colors = [color_map[c[0]] for c in coach_seq]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    fig.suptitle(f'{team} — Season Performance & Coaches', fontsize=14, fontweight='bold')

    bars = ax1.bar(years, points, color=bar_colors, edgecolor='white', linewidth=0.5)
    ax1.axhline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)
    ax1.set_ylabel('Season Points')
    for bar, pt in zip(bars, points):
        offset = 8 if pt >= 0 else -18
        ax1.annotate(f'{pt:+}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                     xytext=(0, offset), textcoords='offset points',
                     ha='center', fontsize=7.5)

    ax2.plot(years, ranks, 'o-', color='#333', linewidth=2, markersize=6, zorder=3)
    for yr, rk, clr in zip(years, ranks, bar_colors):
        ax2.plot(yr, rk, 'o', color=clr, markersize=9, zorder=4)
        ax2.annotate(f'#{rk}', xy=(yr, rk), xytext=(0, 8),
                     textcoords='offset points', ha='center', fontsize=7.5)
    ax2.invert_yaxis()
    ax2.set_ylabel('Final Rank (lower = better)')
    ax2.set_xlabel('Season')
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, rotation=45)

    def dep_symbol(dep):
        return {'fired': '🔥', 'retired': '🎓', 'resigned': '→', 'active': '✓'}.get(dep, '')

    patches = [mpatches.Patch(color=color_map[c[0]],
               label=f'{c[0]} ({dep_symbol(c[1])} {c[1]})') for c in seen_coaches]
    fig.legend(handles=patches, title='Head Coach', loc='lower right',
               bbox_to_anchor=(0.98, 0.02), fontsize=8, title_fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 1])
    out = os.path.join(OUT_DIR, f'{team.replace(" ", "_")}_history.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved: {out}')


def print_trending_table(trends, top_n=25):
    print(f'\n{"="*70}')
    print(f'TOP {top_n} TRENDING UP TEAMS (recent 3yr avg vs prior avg)')
    print(f'{"="*70}')
    print(f'{"Rank":<5} {"Team":<22} {"Trend":>7} {"Recent Avg":>11} {"Prior Avg":>10} {"Current Coach":<22}')
    print(f'{"-"*5} {"-"*22} {"-"*7} {"-"*11} {"-"*10} {"-"*22}')
    for i, (team, score, slope, recent, prior, coach) in enumerate(trends[:top_n], 1):
        print(f'{i:<5} {team:<22} {score:>+7.0f} {recent:>11.0f} {prior:>10.0f} {coach:<22}')
    print()


def print_fired_table(tenure_stats):
    fired = [r for r in tenure_stats if r['departure'] == 'fired' and r['seasons'] >= 1]
    fired.sort(key=lambda x: x['avg_points'])

    print(f'\n{"="*85}')
    print('FIRED COACHES — Performance Summary')
    print(f'{"="*85}')
    print(f'{"Coach":<22} {"Team":<15} {"Yrs":<12} {"Seasons":>7} {"AvgPts":>8} {"AvgRank":>8} {"Slope":>7}')
    print(f'{"-"*22} {"-"*15} {"-"*12} {"-"*7} {"-"*8} {"-"*8} {"-"*7}')
    for r in fired:
        yrs = f'{r["start_year"]}–{r["end_year"]}'
        print(f'{r["coach"]:<22} {r["team"]:<15} {yrs:<12} {r["seasons"]:>7} '
              f'{r["avg_points"]:>8.0f} {r["avg_rank"]:>8.1f} {r["slope"]:>+7.0f}')
    print()


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    coaches = load_coaches()
    season_data = load_all_season_points()
    tenure_stats = coach_tenure_stats(coaches, season_data)
    trends = compute_trends(season_data, coaches, recent_n=3)

    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if cmd in ('trends', 'all'):
        print_trending_table(trends, top_n=25)
        plot_trending_teams(trends, top_n=20)

    if cmd in ('fired', 'all'):
        print_fired_table(tenure_stats)
        plot_fired_coach_profiles(tenure_stats)

    if cmd in ('all',):
        # Regenerate Nebraska with full coach DB
        plot_team_with_coaches('Nebraska', season_data, coaches)

    if cmd == 'team' and len(sys.argv) > 2:
        team = ' '.join(sys.argv[2:])
        plot_team_with_coaches(team, season_data, coaches)

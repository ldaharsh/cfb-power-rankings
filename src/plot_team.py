"""
Plot a team's season points over time with coach annotations.
Usage: python plot_team.py "Nebraska"
"""

import os
import sys
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

RANKINGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'rankings')

# Known head coaches by team and year range (inclusive)
COACHES = {
    'Nebraska': [
        (2014, 2014, 'Bo Pelini'),
        (2015, 2017, 'Mike Riley'),
        (2018, 2022, 'Scott Frost'),   # Frost fired week 5 of 2022
        (2022, 2022, 'Scott Frost / M. Joseph'),  # handled below
        (2023, 2025, 'Matt Rhule'),
    ],
}

# Fine-grained overrides for mid-season firings
COACH_BY_YEAR = {
    'Nebraska': {
        2014: 'Bo Pelini',
        2015: 'Mike Riley',
        2016: 'Mike Riley',
        2017: 'Mike Riley',
        2018: 'Scott Frost',
        2019: 'Scott Frost',
        2020: 'Scott Frost',
        2021: 'Scott Frost',
        2022: 'Frost / M. Joseph',
        2023: 'Matt Rhule',
        2024: 'Matt Rhule',
        2025: 'Matt Rhule',
    }
}

# Color per coach (auto-assigned if not listed)
COACH_COLORS = [
    '#e41a1c', '#377eb8', '#4daf4a', '#984ea3',
    '#ff7f00', '#a65628', '#f781bf', '#999999',
]


def get_team_data(team):
    rows = []
    for year in range(2014, 2026):
        path = os.path.join(RANKINGS_DIR, f'{year}_season.csv')
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for row in csv.DictReader(f):
                if row['team'] == team:
                    rows.append({
                        'year': year,
                        'rank': int(row['final_rank']),
                        'points': int(row['season_points']),
                        'preseason_rank': row['preseason_rank'],
                    })
    return rows


def plot_team(team):
    data = get_team_data(team)
    if not data:
        print(f'No data found for "{team}"')
        return

    years = [d['year'] for d in data]
    points = [d['points'] for d in data]
    ranks = [d['rank'] for d in data]

    coach_map = COACH_BY_YEAR.get(team, {})
    coaches_ordered = []
    seen = []
    for y in years:
        c = coach_map.get(y, 'Unknown')
        if c not in seen:
            seen.append(c)
        coaches_ordered.append(c)

    color_map = {c: COACH_COLORS[i % len(COACH_COLORS)] for i, c in enumerate(seen)}
    bar_colors = [color_map[c] for c in coaches_ordered]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle(f'{team} — Season Performance by Year', fontsize=14, fontweight='bold')

    # Top chart: season points
    bars = ax1.bar(years, points, color=bar_colors, edgecolor='white', linewidth=0.5)
    ax1.axhline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)
    ax1.set_ylabel('Season Points')
    ax1.set_title('Season Points (positive = above expectations, negative = below)')

    # Annotate bars with point values
    for bar, pt in zip(bars, points):
        ypos = bar.get_height() if pt >= 0 else bar.get_height()
        offset = 8 if pt >= 0 else -18
        ax1.annotate(f'{pt:+}', xy=(bar.get_x() + bar.get_width() / 2, ypos),
                     xytext=(0, offset), textcoords='offset points',
                     ha='center', va='bottom', fontsize=7.5)

    # Bottom chart: final rank (inverted — lower rank # = better)
    ax2.plot(years, ranks, 'o-', color='#333333', linewidth=2, markersize=6, zorder=3)
    for i, (yr, rk, c) in enumerate(zip(years, ranks, bar_colors)):
        ax2.plot(yr, rk, 'o', color=c, markersize=9, zorder=4)
        ax2.annotate(f'#{rk}', xy=(yr, rk), xytext=(0, 8),
                     textcoords='offset points', ha='center', fontsize=7.5)

    ax2.invert_yaxis()
    ax2.set_ylabel('Final Rank')
    ax2.set_title('Final Season Rank (lower = better)')
    ax2.set_xlabel('Season')
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, rotation=45)

    # Coach legend
    patches = [mpatches.Patch(color=color_map[c], label=c) for c in seen]
    fig.legend(handles=patches, title='Head Coach', loc='lower right',
               bbox_to_anchor=(0.98, 0.02), fontsize=9, title_fontsize=9)

    plt.tight_layout(rect=[0, 0.0, 1, 1])

    out_path = os.path.join(os.path.dirname(__file__), '..', f'{team.replace(" ", "_")}_history.png')
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f'Saved: {out_path}')
    plt.close()


if __name__ == '__main__':
    team = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Nebraska'
    plot_team(team)

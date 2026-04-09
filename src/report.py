"""
Generate readable ranking tables from computed CSV data.
Usage:
  python report.py --year 2023       # single season
  python report.py --alltime         # all-time program rankings
  python report.py --year 2023 --top 25   # top 25 for a season
"""

import os
import csv
import argparse

RANKINGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'rankings')


def load_season(year):
    path = os.path.join(RANKINGS_DIR, f'{year}_season.csv')
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    rows.sort(key=lambda r: int(r['final_rank']))
    return rows


def load_alltime():
    path = os.path.join(RANKINGS_DIR, 'alltime.csv')
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    rows.sort(key=lambda r: int(r['rank']))
    return rows


def print_table(headers, rows, col_widths=None):
    if col_widths is None:
        col_widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    fmt = '  '.join(f'{{:<{w}}}' for w in col_widths)
    sep = '  '.join('-' * w for w in col_widths)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))


def show_season(year, top=None):
    rows = load_season(year)
    if rows is None:
        print(f'No season data for {year}. Run engine.py first.')
        return

    if top:
        rows = [r for r in rows if int(r['final_rank']) <= top]

    print(f'\n=== {year} Season Final Rankings ===\n')
    table_rows = [
        (r['final_rank'], r['team'], r['season_points'], r['preseason_rank'])
        for r in rows
    ]
    print_table(
        ['Rank', 'Team', 'Points', 'Preseason Rank'],
        table_rows,
        col_widths=[6, 25, 8, 15],
    )
    print()


def show_alltime(top=None):
    rows = load_alltime()
    if rows is None:
        print('No all-time data. Run engine.py first.')
        return

    if top:
        rows = [r for r in rows if int(r['rank']) <= top]

    print('\n=== All-Time Program Rankings ===\n')
    table_rows = [(r['rank'], r['team'], r['total_points']) for r in rows]
    print_table(
        ['Rank', 'Team', 'Total Points'],
        table_rows,
        col_widths=[6, 25, 12],
    )
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int)
    parser.add_argument('--alltime', action='store_true')
    parser.add_argument('--top', type=int)
    args = parser.parse_args()

    if args.year:
        show_season(args.year, args.top)
    if args.alltime:
        show_alltime(args.top)
    if not args.year and not args.alltime:
        # Show all available seasons + alltime
        for year in range(2014, 2026):
            rows = load_season(year)
            if rows:
                show_season(year, args.top)
        show_alltime(args.top)

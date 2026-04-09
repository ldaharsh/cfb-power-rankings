"""
Power Rankings - Main entry point.

Steps:
  1. python main.py parse       - Parse Phil Steel HTML files into preseason CSVs
  2. python main.py fetch       - Fetch game results from CFBD API
  3. python main.py run         - Run ranking engine, produce season + all-time rankings
  4. python main.py report      - Print ranking tables

Or run all steps: python main.py all

Environment variable required for fetch step:
  CFBD_API_KEY=your_key_here
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def cmd_parse():
    from parse_html import parse_all
    print('=== Parsing Phil Steel HTML files ===')
    parse_all()


def cmd_fetch(args):
    import src.fetch_games as fg
    api_key = os.environ.get('CFBD_API_KEY', '')
    if not api_key:
        print('Set CFBD_API_KEY environment variable first.')
        print('Get a free key at: https://collegefootballdata.com/key')
        sys.exit(1)
    print('=== Fetching game results from CFBD ===')
    years = [int(a) for a in args] if args else None
    fg.fetch_all(api_key, years)


def cmd_run():
    from engine import run_all_seasons
    print('=== Running ranking engine ===')
    run_all_seasons()


def cmd_report(args):
    from report import show_season, show_alltime
    top = None
    year = None
    alltime = False
    for a in args:
        if a == '--alltime':
            alltime = True
        elif a.startswith('--top='):
            top = int(a.split('=')[1])
        elif a.isdigit():
            year = int(a)
    if year:
        show_season(year, top)
    if alltime:
        show_alltime(top)
    if not year and not alltime:
        for y in range(2014, 2026):
            show_season(y, top)
        show_alltime(top)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == 'parse':
        cmd_parse()
    elif cmd == 'fetch':
        cmd_fetch(rest)
    elif cmd == 'run':
        cmd_run()
    elif cmd == 'report':
        cmd_report(rest)
    elif cmd == 'all':
        cmd_parse()
        cmd_fetch(rest)
        cmd_run()
        cmd_report(['--alltime', '--top=25'])
    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)

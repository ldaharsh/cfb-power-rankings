"""
Parse Phil Steel's FBS Power Ratings HTML files.
Extracts preseason (Start) and end-of-season (Current) power ratings.
Outputs: data/preseason/{year}_preseason.csv with columns: team, start_rating, current_rating
"""

import os
import re
import csv
from bs4 import BeautifulSoup


HTML_DIR = os.path.join(os.path.dirname(__file__), '..', '')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'preseason')

YEARS = list(range(14, 26))  # 14..25


def get_cell_text(td):
    return td.get_text(strip=True)


def is_number(s):
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def parse_year(year_short):
    year_full = 2000 + year_short
    html_path = os.path.join(HTML_DIR, f'{year_short}.html')
    with open(html_path, encoding='windows-1252', errors='replace') as f:
        soup = BeautifulSoup(f, 'lxml')

    teams = {}  # name -> (start, current)

    # Find all tables and look for ones containing "Start" and "Current" headers
    for table in soup.find_all('table'):
        text = table.get_text()
        if 'Start' not in text or ('Current' not in text and 'Final' not in text):
            continue
        # Make sure this looks like a power ratings table (has conference names)
        conferences = ['SEC', 'BIG TEN', 'BIG 12', 'PAC', 'ACC', 'AAC', 'MAC',
                       'MOUNTAIN WEST', 'SUN BELT', 'CONFERENCE USA', 'INDEPENDENT']
        if not any(c in text for c in conferences):
            continue

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            # Each row has up to 3 (team, start, current) groups separated by spacer cells
            # Layout: [team, start, current, spacer, team, start, current, spacer, team, start, current]
            # We scan each group of 3 consecutive cells (indices 0,1,2 / 4,5,6 / 8,9,10)
            offsets = [0, 4, 8]
            for offset in offsets:
                if offset + 2 >= len(cells):
                    break
                name_cell = cells[offset]
                start_cell = cells[offset + 1]
                cur_cell = cells[offset + 2]

                name = get_cell_text(name_cell)
                start = get_cell_text(start_cell)
                current = get_cell_text(cur_cell)

                # Skip header rows, empty rows, or non-numeric values
                if not name or not is_number(start) or not is_number(current):
                    continue
                # Skip if name looks like a number (shouldn't happen but guard anyway)
                if is_number(name):
                    continue
                # Skip known header/label strings
                if name.upper() in ('START', 'CURRENT', 'N/A', '&NBSP;'):
                    continue

                name_clean = clean_name(name)
                start_val = int(start)
                cur_val = int(current)

                if name_clean in teams:
                    # Keep first occurrence (shouldn't duplicate, but just in case)
                    continue
                teams[name_clean] = (start_val, cur_val)

        # Once we've found the right table and extracted data, stop
        if teams:
            break

    return year_full, teams


def clean_name(name):
    """Normalize team name: strip whitespace, collapse internal spaces."""
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def save_year(year_full, teams):
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f'{year_full}_preseason.csv')

    # Sort by start rating descending to assign preseason rank
    sorted_teams = sorted(teams.items(), key=lambda x: x[1][0], reverse=True)

    # Handle ties: teams with same start rating share the same rank (worst/lowest of tied positions)
    n = len(sorted_teams)
    rows = []
    i = 0
    while i < n:
        j = i
        # Find all teams tied at this start rating
        while j < n and sorted_teams[j][1][0] == sorted_teams[i][1][0]:
            j += 1
        # All in [i, j) are tied; assign rank = j (worst position in the tie group)
        for k in range(i, j):
            team_name, (start, current) = sorted_teams[k]
            rows.append({
                'team': team_name,
                'preseason_rank': j,
                'start_rating': start,
                'current_rating': current,
            })
        i = j

    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['team', 'preseason_rank', 'start_rating', 'current_rating'])
        writer.writeheader()
        writer.writerows(rows)

    return out_path, len(rows)


def parse_all():
    for yr in YEARS:
        year_full, teams = parse_year(yr)
        if not teams:
            print(f'WARNING: No teams found for {year_full}')
            continue
        path, count = save_year(year_full, teams)
        print(f'{year_full}: {count} teams -> {os.path.basename(path)}')


if __name__ == '__main__':
    parse_all()

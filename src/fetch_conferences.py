"""
Extract team→conference mapping from Phil Steel HTML files.
Outputs: data/conferences.csv  (team, year, conference)
"""
import os, csv, re
from bs4 import BeautifulSoup

HTML_DIR = os.path.join(os.path.dirname(__file__), '..')
OUT = os.path.join(HTML_DIR, 'data', 'conferences.csv')
YEARS = list(range(14, 26))

CONF_ALIASES = {
    'PAC-12': 'Pac-12', 'PAC-2': 'Pac-12', 'PAC 12': 'Pac-12',
    'BIG TEN': 'Big Ten', 'BIG 10': 'Big Ten',
    'BIG 12': 'Big 12', 'BIG12': 'Big 12',
    'ACC': 'ACC', 'SEC': 'SEC', 'AAC': 'AAC',
    'MOUNTAIN WEST': 'Mountain West', 'MW': 'Mountain West',
    'CONFERENCE USA': 'C-USA', 'CUSA': 'C-USA',
    'MAC': 'MAC', 'SUN BELT': 'Sun Belt', 'SBC': 'Sun Belt',
    'INDEPENDENT': 'Independent', 'INDEPENDENTS': 'Independent',
}

def norm_conf(raw):
    r = raw.strip().upper()
    for k, v in CONF_ALIASES.items():
        if k in r:
            return v
    return raw.strip().title()

def is_number(s):
    try: int(s); return True
    except: return False

def parse_year(yr_short):
    year = 2000 + yr_short
    path = os.path.join(HTML_DIR, f'{yr_short}.html')
    soup = BeautifulSoup(open(path, encoding='windows-1252', errors='replace'), 'lxml')
    results = {}

    for table in soup.find_all('table'):
        txt = table.get_text()
        if 'Start' not in txt: continue
        if not any(c in txt for c in ['SEC','BIG TEN','ACC','BIG 12','PAC']): continue

        rows = table.find_all('tr')
        # current conference assignment for each of 3 column groups
        conf_map = {0: None, 4: None, 8: None}

        for row in rows:
            cells = row.find_all('td')
            if not cells: continue

            # Detect conference header row: has a cell with colspan=3 and no numeric data
            header_cells = [c for c in cells if c.get('colspan') in ('3', 3)]
            if header_cells:
                conf_texts = [norm_conf(c.get_text()) for c in header_cells
                              if c.get_text(strip=True) and
                              not any(w in c.get_text() for w in ['Start','Current','Final','Updated','Plus','Minus','Preseason'])]
                if conf_texts:
                    offsets = [0, 4, 8]
                    for i, ct in enumerate(conf_texts[:3]):
                        conf_map[offsets[i]] = ct
                continue

            # Data row
            for offset in (0, 4, 8):
                if offset + 2 >= len(cells): break
                name = cells[offset].get_text(strip=True)
                start = cells[offset+1].get_text(strip=True)
                if not name or not is_number(start) or is_number(name): continue
                conf = conf_map.get(offset)
                if conf and name not in results:
                    results[name] = conf

        if results: break

    return year, results

def run():
    all_rows = []
    for yr in YEARS:
        year, mapping = parse_year(yr)
        for team, conf in mapping.items():
            all_rows.append({'year': year, 'team': team, 'conference': conf})
        print(f'{year}: {len(mapping)} teams')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['year','team','conference'])
        w.writeheader(); w.writerows(all_rows)
    print(f'Saved {len(all_rows)} rows -> {OUT}')

if __name__ == '__main__':
    run()

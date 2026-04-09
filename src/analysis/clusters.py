"""Program trajectory clustering using season points history."""
import os, csv, sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
YEARS = list(range(2014, 2026))

CLUSTER_LABELS = {
    0: 'Perennial Elite',
    1: 'Rising Program',
    2: 'Declining Power',
    3: 'Consistent Mid-Tier',
    4: 'Rebuilding',
    5: 'Bottom Dweller',
}

def build_matrix():
    """Build team × year points matrix for Steel-ranked teams."""
    steel = set()
    for yr in YEARS:
        p = os.path.join(DATA, 'preseason', f'{yr}_preseason.csv')
        if os.path.exists(p):
            with open(p) as f:
                for r in csv.DictReader(f): steel.add(r['team'])

    pts = {t: {} for t in steel}
    for yr in YEARS:
        p = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
        if not os.path.exists(p): continue
        with open(p) as f:
            for r in csv.DictReader(f):
                if r['team'] in pts:
                    pts[r['team']][yr] = int(r['season_points'])

    rows = []
    for team, yr_pts in pts.items():
        if len(yr_pts) < 6: continue  # need enough data
        row = {'team': team}
        for yr in YEARS:
            row[str(yr)] = yr_pts.get(yr, np.nan)
        rows.append(row)

    df = pd.DataFrame(rows).set_index('team')
    df = df.fillna(df.median())
    return df

def cluster_programs(n_clusters=6, random_state=42):
    df = build_matrix()
    scaler = StandardScaler()
    X = scaler.fit_transform(df.values)

    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = km.fit_predict(X)

    # PCA for 2D visualization
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)

    result = df.copy()
    result['cluster'] = labels
    result['pca_x'] = coords[:, 0]
    result['pca_y'] = coords[:, 1]

    # Assign human-readable cluster names based on cluster centroid mean
    cluster_means = {}
    for cl in range(n_clusters):
        mask = labels == cl
        cluster_means[cl] = X[mask].mean()

    sorted_clusters = sorted(cluster_means.items(), key=lambda x: x[1], reverse=True)
    rename_map = {}
    fixed_labels = ['Perennial Elite', 'Consistent Strong', 'Rising Program',
                    'Mid-Tier', 'Declining / Volatile', 'Bottom Tier']
    for rank, (cl, _) in enumerate(sorted_clusters):
        rename_map[cl] = fixed_labels[rank] if rank < len(fixed_labels) else f'Cluster {cl}'

    result['cluster_label'] = result['cluster'].map(rename_map)

    # Add summary stats
    result['avg_pts'] = df.mean(axis=1)
    result['trend'] = df.apply(
        lambda row: np.polyfit(range(len(row)), row.values, 1)[0], axis=1)

    return result[['cluster','cluster_label','avg_pts','trend','pca_x','pca_y']]

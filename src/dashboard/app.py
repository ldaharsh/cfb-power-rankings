"""
Power Rankings Dashboard — Streamlit app.
Run: streamlit run src/dashboard/app.py
"""
import os, sys, csv
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'src'))
DATA = os.path.join(ROOT, 'data')
YEARS = list(range(2014, 2026))

st.set_page_config(page_title='CFB Power Rankings', layout='wide',
                   page_icon='🏈', initial_sidebar_state='expanded')

# ── helpers ───────────────────────────────────────────────────────────────────

@st.cache_data
def load_alltime():
    p = os.path.join(DATA, 'rankings', 'alltime.csv')
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_data
def load_all_seasons():
    rows = []
    for yr in YEARS:
        p = os.path.join(DATA, 'rankings', f'{yr}_season.csv')
        if not os.path.exists(p): continue
        df = pd.read_csv(p); df['year'] = yr
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

@st.cache_data
def load_conferences():
    p = os.path.join(DATA, 'conferences.csv')
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_data
def load_coaches():
    p = os.path.join(DATA, 'coaches.csv')
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_data
def load_weekly():
    rows = []
    for yr in YEARS:
        p = os.path.join(DATA, 'rankings', f'{yr}_weekly.csv')
        if not os.path.exists(p): continue
        df = pd.read_csv(p); rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

@st.cache_data
def load_accuracy():
    from analysis.accuracy import load
    return load()

@st.cache_data
def load_clusters():
    from analysis.clusters import cluster_programs
    return cluster_programs()

@st.cache_data
def load_cfp():
    from analysis.cfp import cfp_prediction_table, weekly_rank_of_champion
    return cfp_prediction_table(), weekly_rank_of_champion()

@st.cache_data
def load_sos():
    from analysis.sos import sos_all_years
    return sos_all_years()

@st.cache_data
def coach_tenure_df():
    from analysis.coaching_deep import load_tenure_df
    return load_tenure_df()

def get_coach(coaches_df, team, year):
    mask = (coaches_df['team']==team) & (coaches_df['start_year']<=year) & (coaches_df['end_year']>=year)
    m = coaches_df[mask]
    return m['coach'].iloc[0] if len(m) else 'Unknown'

# ── sidebar nav ───────────────────────────────────────────────────────────────

st.sidebar.title('🏈 CFB Power Rankings')
st.sidebar.caption('Phil Steel-based system, 2014–2025')
page = st.sidebar.radio('Navigate', [
    '🏆 All-Time Rankings',
    '📅 Season View',
    '🔍 Team Explorer',
    '📈 Trending Teams',
    '🏛️ Conference Power',
    '🎓 Coaching Analysis',
    '🎯 CFP Predictability',
    '🎲 Phil Steel Accuracy',
    '⚖️ Strength of Schedule',
    '🗂️ Program Clusters',
])

# ── page: All-Time Rankings ───────────────────────────────────────────────────

if page == '🏆 All-Time Rankings':
    st.title('🏆 All-Time Program Rankings (2014–2025)')
    df = load_alltime()
    if df.empty:
        st.warning('No data. Run: python main.py run')
    else:
        top_n = st.slider('Show top N teams', 10, len(df), 25)
        show = df.head(top_n).copy()
        fig = px.bar(show, x='team', y='total_points', color='total_points',
                     color_continuous_scale='Blues',
                     labels={'total_points':'Total Points','team':'Team'},
                     title=f'Top {top_n} Programs — Cumulative Season Points')
        fig.update_layout(xaxis_tickangle=-45, showlegend=False,
                          coloraxis_showscale=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns([3,2])
        with col1:
            st.dataframe(show.rename(columns={'rank':'Rank','team':'Team','total_points':'Total Pts'}),
                         use_container_width=True, hide_index=True)
        with col2:
            st.metric('👑 #1 All-Time', df.iloc[0]['team'])
            st.metric('📊 Avg Points (Top 10)', f"{df.head(10)['total_points'].mean():.0f}")
            gap = df.iloc[0]['total_points'] - df.iloc[1]['total_points']
            st.metric(f"Gap #1 → #2", f"{gap:,.0f} pts")

# ── page: Season View ─────────────────────────────────────────────────────────

elif page == '📅 Season View':
    st.title('📅 Season Rankings')
    all_sea = load_all_seasons()
    coaches_df = load_coaches()
    yr = st.select_slider('Season', YEARS, value=2024)
    sea = all_sea[all_sea['year']==yr].copy()
    sea = sea.sort_values('final_rank')
    top_n = st.slider('Show top N', 10, min(len(sea),130), 25)
    sea = sea.head(top_n)
    sea['coach'] = sea.apply(lambda r: get_coach(coaches_df, r['team'], yr), axis=1)

    fig = px.bar(sea, x='team', y='season_points', color='season_points',
                 color_continuous_scale='RdYlGn', hover_data=['final_rank','preseason_rank','coach'],
                 title=f'{yr} Season Final Rankings — Top {top_n}')
    fig.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sea[['final_rank','team','season_points','preseason_rank','coach']]
                 .rename(columns={'final_rank':'Rank','team':'Team','season_points':'Points',
                                  'preseason_rank':'Preseason','coach':'Coach'}),
                 use_container_width=True, hide_index=True)

# ── page: Team Explorer ───────────────────────────────────────────────────────

elif page == '🔍 Team Explorer':
    st.title('🔍 Team Explorer')
    all_sea = load_all_seasons()
    coaches_df = load_coaches()
    weekly_df = load_weekly()

    all_teams = sorted(all_sea['team'].unique())
    teams = st.multiselect('Select teams to compare', all_teams,
                           default=['Alabama','Ohio St','Georgia'])
    if not teams:
        st.info('Select at least one team.')
        st.stop()

    metric = st.radio('Metric', ['Season Points', 'Final Rank'], horizontal=True)
    col = 'season_points' if metric == 'Season Points' else 'final_rank'
    inv = metric == 'Final Rank'

    sub = all_sea[all_sea['team'].isin(teams)].copy()
    sub['coach'] = sub.apply(lambda r: get_coach(coaches_df, r['team'], r['year']), axis=1)

    fig = go.Figure()
    colors = px.colors.qualitative.Set1
    for i, team in enumerate(teams):
        td = sub[sub['team']==team].sort_values('year')
        fig.add_trace(go.Scatter(
            x=td['year'], y=td[col], mode='lines+markers',
            name=team, line=dict(color=colors[i%len(colors)], width=2.5),
            hovertemplate=f'<b>{team}</b><br>%{{x}}: %{{y}}<br>Coach: %{{customdata}}',
            customdata=td['coach'].values,
        ))
    if inv: fig.update_yaxes(autorange='reversed')
    fig.update_layout(title=f'{metric} by Season', xaxis_title='Season',
                      yaxis_title=metric, height=450, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    # Weekly rank progression for selected season
    if not weekly_df.empty:
        yr_sel = st.select_slider('In-season progression — year', YEARS, value=2024,
                                  key='team_wk_yr')
        wk_sub = weekly_df[(weekly_df['year']==yr_sel) & (weekly_df['team'].isin(teams))]
        if not wk_sub.empty:
            fig2 = px.line(wk_sub, x='week', y='rank', color='team',
                           title=f'{yr_sel} Week-by-Week Rankings',
                           markers=True)
            fig2.update_yaxes(autorange='reversed')
            fig2.update_layout(height=380, xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

    # Stats table
    st.subheader('Career Summary')
    summary = (sub.groupby('team').agg(
        Seasons=('year','count'), Avg_Pts=('season_points','mean'),
        Best_Rank=('final_rank','min'), Worst_Rank=('final_rank','max'))
        .round(1).reset_index())
    st.dataframe(summary, use_container_width=True, hide_index=True)

# ── page: Trending Teams ──────────────────────────────────────────────────────

elif page == '📈 Trending Teams':
    st.title('📈 Trending Teams')
    from coaching_analysis import load_coaches as lc2, load_all_season_points, compute_trends
    coaches = lc2(); season_data = load_all_season_points()
    trends = compute_trends(season_data, coaches, recent_n=3)
    df = pd.DataFrame(trends, columns=['team','trend_score','slope','recent_avg','prior_avg','current_coach'])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('🔼 Top 20 Trending Up')
        top = df.head(20)
        fig = px.bar(top, x='team', y='trend_score', color='trend_score',
                     color_continuous_scale='Greens', hover_data=['current_coach','recent_avg','prior_avg'],
                     title='Biggest improvement: recent 3yr avg vs prior')
        fig.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=420)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader('🔽 Top 20 Trending Down')
        bot = df.tail(20).sort_values('trend_score')
        fig2 = px.bar(bot, x='team', y='trend_score', color='trend_score',
                      color_continuous_scale='Reds_r', hover_data=['current_coach','recent_avg','prior_avg'])
        fig2.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=420)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader('All teams — trend score')
    st.dataframe(df[['team','trend_score','recent_avg','prior_avg','current_coach']]
                 .rename(columns={'trend_score':'Trend','recent_avg':'Recent Avg (3yr)',
                                  'prior_avg':'Prior Avg','current_coach':'Current Coach'})
                 .round(0), use_container_width=True, hide_index=True)

# ── page: Conference Power ────────────────────────────────────────────────────

elif page == '🏛️ Conference Power':
    st.title('🏛️ Conference Power Over Time')
    from analysis.conferences import load as load_conf_data, conf_power_by_year, MAJOR_CONFS
    df = load_conf_data()
    agg = conf_power_by_year(df)

    confs = st.multiselect('Conferences', sorted(agg['conference'].unique()),
                           default=[c for c in MAJOR_CONFS if c in agg['conference'].unique()])
    if confs:
        sub = agg[agg['conference'].isin(confs)]
        fig = px.line(sub, x='year', y='avg_pts', color='conference', markers=True,
                      title='Average Season Points by Conference per Year',
                      labels={'avg_pts':'Avg Season Points','year':'Season'})
        fig.update_layout(height=500, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

        # Heatmap
        pivot = sub.pivot(index='conference', columns='year', values='avg_pts').fillna(0)
        fig2 = px.imshow(pivot, color_continuous_scale='RdYlGn', aspect='auto',
                         title='Conference Strength Heatmap')
        st.plotly_chart(fig2, use_container_width=True)

        # Animated race-style bar chart
        st.subheader('Season-by-season race')
        fig3 = px.bar(sub.sort_values(['year','avg_pts'], ascending=[True,False]),
                      x='conference', y='avg_pts', animation_frame='year',
                      color='conference', range_y=[sub['avg_pts'].min()-50, sub['avg_pts'].max()+50],
                      title='Conference Power Race')
        fig3.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

# ── page: Coaching Analysis ───────────────────────────────────────────────────

elif page == '🎓 Coaching Analysis':
    st.title('🎓 Coaching Analysis')
    from analysis.coaching_deep import honeymoon_effect, recycled_coaches, portal_era_split
    tenure_df = coach_tenure_df()

    tab1, tab2, tab3, tab4 = st.tabs(['Best Coaches','Honeymoon Effect','Recycled Coaches','Portal Era'])

    with tab1:
        from coaching_analysis import load_coaches as lc2, load_all_season_points, coach_tenure_stats
        coaches = lc2(); season_data = load_all_season_points()
        stats = coach_tenure_stats(coaches, season_data)
        df_stats = pd.DataFrame(stats)
        min_s = st.slider('Min seasons coached', 1, 10, 3)
        df_q = df_stats[df_stats['seasons']>=min_s].sort_values('avg_points', ascending=False)
        st.subheader(f'Best Coaches (≥{min_s} seasons)')
        fig = px.scatter(df_q.head(50), x='avg_points', y='avg_rank', color='departure',
                         size='seasons', hover_data=['coach','team','start_year','end_year'],
                         title='Coach Performance: Avg Points vs Avg Rank',
                         color_discrete_map={'active':'#2ca02c','retired':'#1f77b4',
                                             'resigned':'#ff7f0e','fired':'#d62728'})
        fig.update_yaxes(autorange='reversed')
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_q[['coach','team','start_year','end_year','seasons','avg_points','avg_rank','slope','departure']]
                     .head(40).round(1), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader('Honeymoon Effect — Avg Points by Tenure Year')
        hm = honeymoon_effect(tenure_df)
        fig = px.bar(hm.reset_index(), x='tenure_bucket', y='avg_pts',
                     error_y='se', color='avg_pts', color_continuous_scale='RdYlGn',
                     title='Does performance improve over time in a tenure?')
        fig.update_layout(coloraxis_showscale=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(hm.round(1), use_container_width=True)

    with tab3:
        st.subheader('Recycled Coaches — Job 1 vs Job 2 Performance')
        rec = recycled_coaches(tenure_df)
        if not rec.empty:
            fig = px.scatter(rec, x='job1_avg', y='job2_avg', text='coach',
                             color='delta', color_continuous_scale='RdYlGn',
                             hover_data=['job1_team','job2_team','job1_departure'],
                             title='Did fired/resigned coaches do better at their next job?')
            fig.add_shape(type='line', x0=rec['job1_avg'].min(), y0=rec['job1_avg'].min(),
                          x1=rec['job1_avg'].max(), y1=rec['job1_avg'].max(),
                          line=dict(dash='dash', color='gray'))
            fig.update_traces(textposition='top center', textfont_size=8)
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(rec.sort_values('delta', ascending=False).round(1),
                         use_container_width=True, hide_index=True)

    with tab4:
        st.subheader('Transfer Portal Era — Before (≤2020) vs After (≥2021)')
        pe = portal_era_split(tenure_df)
        pe = pe.reset_index()
        pe = pe.sort_values('delta', ascending=False)
        fig = px.bar(pe.head(30), x='team', y='delta', color='delta',
                     color_continuous_scale='RdYlGn',
                     hover_data=['pre_avg','post_avg'],
                     title='Points change in portal era (top 30 gainers)')
        fig.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('**Biggest Portal Winners**')
            st.dataframe(pe.head(15).round(1), use_container_width=True, hide_index=True)
        with col2:
            st.markdown('**Biggest Portal Losers**')
            st.dataframe(pe.tail(15).sort_values('delta').round(1), use_container_width=True, hide_index=True)

# ── page: CFP Predictability ──────────────────────────────────────────────────

elif page == '🎯 CFP Predictability':
    st.title('🎯 CFP Predictability')
    cfp_table, champ_wk = load_cfp()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Our Rankings vs CFP Selection')
        st.dataframe(cfp_table, use_container_width=True)
        acc4 = cfp_table['top4_overlap'].mean()
        champ_in4 = cfp_table['champ_in_our_top4'].mean() * 100
        st.metric('Avg overlap with CFP 4-team field', f'{acc4:.1f} / 4 teams')
        st.metric('Champion in our Top 4 (%)', f'{champ_in4:.0f}%')
    with col2:
        st.subheader('How early does champion reach our Top 3?')
        if not champ_wk.empty:
            st.dataframe(champ_wk, use_container_width=True)
        st.subheader("Champion's final rank in our system")
        fig = px.bar(cfp_table.reset_index(), x='year', y='our_champ_rank',
                     color='champ_in_our_top4',
                     color_discrete_map={True:'#2ca02c', False:'#d62728'},
                     title="CFP Champion's rank in our final standings",
                     labels={'our_champ_rank':'Our Rank','champ_in_our_top4':'In Our Top 4'})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

# ── page: Phil Steel Accuracy ─────────────────────────────────────────────────

elif page == '🎲 Phil Steel Accuracy':
    st.title('🎲 Phil Steel Preseason Accuracy')
    from analysis.accuracy import team_accuracy, year_accuracy, biggest_surprises
    df = load_accuracy()
    ta = team_accuracy(df).reset_index()
    ya = year_accuracy(df).reset_index()
    over, under = biggest_surprises(df, n=15)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Year-by-year accuracy')
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        fig.add_trace(go.Bar(x=ya['year'], y=ya['mae'], name='Mean Abs Error (ranks)',
                             marker_color='#aec6e8'), secondary_y=False)
        fig.add_trace(go.Scatter(x=ya['year'], y=ya['rank_corr'], name='Rank Correlation',
                                 line=dict(color='#d62728', width=2), mode='lines+markers'),
                      secondary_y=True)
        fig.update_layout(title='Preseason Rank vs Final Rank Accuracy', height=380)
        fig.update_yaxes(title_text='MAE (ranks)', secondary_y=False)
        fig.update_yaxes(title_text='Correlation (higher=better)', secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader('Teams Steel consistently over/underrates')
        top15 = ta.head(15)
        bot15 = ta.tail(15).sort_values('avg_delta')
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(y=top15['team'], x=top15['avg_delta'], orientation='h',
                              name='Outperforms', marker_color='#2ca02c'))
        fig2.add_trace(go.Bar(y=bot15['team'], x=bot15['avg_delta'], orientation='h',
                              name='Underperforms', marker_color='#d62728'))
        fig2.update_layout(title='Avg rank delta (+ = outperforms preseason)',
                           height=420, barmode='overlay')
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader('🚀 Biggest single-season overperformers')
        st.dataframe(over.rename(columns={'delta':'Rank Improvement'}),
                     use_container_width=True, hide_index=True)
    with col4:
        st.subheader('💥 Biggest single-season disappointments')
        st.dataframe(under.rename(columns={'delta':'Rank Drop'}),
                     use_container_width=True, hide_index=True)

# ── page: Strength of Schedule ────────────────────────────────────────────────

elif page == '⚖️ Strength of Schedule':
    st.title('⚖️ Strength of Schedule')
    sos = load_sos()
    yr = st.select_slider('Season', YEARS, value=2024, key='sos_yr')
    sub = sos[sos['year']==yr].copy()
    steel_teams_p = os.path.join(DATA, 'preseason', f'{yr}_preseason.csv')
    if os.path.exists(steel_teams_p):
        steel = pd.read_csv(steel_teams_p)['team'].tolist()
        sub = sub[sub['team'].isin(steel)]

    sub = sub.sort_values('avg_opp_rank')
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f'{yr} Hardest Schedules')
        fig = px.bar(sub.head(20), x='team', y='avg_opp_rank',
                     color='avg_opp_rank', color_continuous_scale='Blues_r',
                     title='Avg opponent rank (lower = harder schedule)')
        fig.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader(f'{yr} Easiest Schedules')
        easy = sub.sort_values('avg_opp_rank', ascending=False).head(20)
        fig2 = px.bar(easy, x='team', y='avg_opp_rank',
                      color='avg_opp_rank', color_continuous_scale='Reds',
                      title='Avg opponent rank (higher = easier schedule)')
        fig2.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=400)
        st.plotly_chart(fig2, use_container_width=True)

    # All-time hardest
    st.subheader('All-time hardest schedule programs (avg opponent rank, lower = tougher)')
    from analysis.sos import hardest_schedules
    hard = hardest_schedules(20).reset_index()
    hard.columns = ['team','avg_opp_rank_alltime']
    hard = hard[hard['team'].isin(
        pd.read_csv(os.path.join(DATA,'rankings','alltime.csv'))['team'].tolist())]
    st.dataframe(hard.round(1), use_container_width=True, hide_index=True)

# ── page: Program Clusters ────────────────────────────────────────────────────

elif page == '🗂️ Program Clusters':
    st.title('🗂️ Program Trajectory Clusters')
    clusters = load_clusters()

    fig = px.scatter(clusters.reset_index(), x='pca_x', y='pca_y',
                     color='cluster_label', text='team',
                     hover_data=['avg_pts','trend'],
                     title='Program Trajectories — PCA of 12-season point history',
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textposition='top center', textfont_size=7.5, marker_size=8)
    fig.update_layout(height=650, legend_title='Cluster')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader('Cluster Breakdown')
    for label in clusters['cluster_label'].unique():
        sub = clusters[clusters['cluster_label']==label].sort_values('avg_pts', ascending=False)
        with st.expander(f'**{label}** ({len(sub)} programs)'):
            st.dataframe(sub[['avg_pts','trend']].reset_index().round(1),
                         use_container_width=True, hide_index=True)

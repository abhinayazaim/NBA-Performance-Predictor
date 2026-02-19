import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
from io import BytesIO
from PIL import Image

# Import backend modules
from data_loader import find_player, get_player_bio, get_active_players_list, fetch_player_game_log, get_opponent_def_ratings, retry_request
from model import predict_next_game, TARGETS
from nba_api.stats.endpoints import scoreboardv2

# --- Page Config & Styling ---
st.set_page_config(
    page_title="CourtVision v2",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Moneyball" aesthetic
st.markdown("""
<style>
    /* Dark Mode Theme Overrides */
    .stApp {
        background-color: #080C14;
        color: #E2E8F0;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-family: 'Bebas Neue', sans-serif !important; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    h1 { color: #FF7A00; text-shadow: 0 0 10px rgba(255, 122, 0, 0.3); }
    h2 { color: #E2E8F0; border-bottom: 2px solid #FF7A00; padding-bottom: 10px; }
    h3 { color: #94A3B8; font-size: 1.2rem !important; }

    /* Metrics Cards */
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        color: #FF7A00 !important;
        font-family: 'Bebas Neue', sans-serif !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-family: 'monospace' !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-family: 'monospace' !important;
        font-size: 0.8rem !important;
    }

    /* DataFrame */
    div[data-testid="stDataFrame"] {
        border: 1px solid #1E293B;
        border-radius: 5px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0F1520;
        border-right: 1px solid #1E293B;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #FF7A00 0%, #E65C00 100%);
        color: white;
        border: none;
        font-weight: bold;
        letter-spacing: 1px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E293B;
        border-radius: 4px 4px 0 0;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF7A00 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---

@st.cache_data(ttl=86400) # Cache daily
def get_roster_options():
    try:
        players = get_active_players_list()
        # Filter top 150? Or just return all names sorted.
        # Let's return all for now, simplified.
        names = sorted([p['full_name'] for p in players])
        return names
    except:
        return []

@st.cache_data(ttl=3600) # Cache hourly
def get_next_game(team_id):
    """
    Finds the next game for a team using ScoreboardV2.
    """
    try:
        # ScoreboardV2 gets games for a specific date. 
        # We need to scan next few days.
        today = datetime.now()
        for i in range(5): # Check next 5 days
            date_str = (today + timedelta(days=i)).strftime('%m/%d/%Y')
            board = retry_request(scoreboardv2.ScoreboardV2, game_date=date_str)
            if board:
                games = board.get_data_frames()[0]
                if not games.empty:
                    # Check both HOME_TEAM_ID and VISITOR_TEAM_ID
                    team_game = games[(games['HOME_TEAM_ID'] == team_id) | (games['VISITOR_TEAM_ID'] == team_id)]
                    if not team_game.empty:
                        game = team_game.iloc[0]
                        # Determine opponent
                        is_home = game['HOME_TEAM_ID'] == team_id
                        opp_id = game['VISITOR_TEAM_ID'] if is_home else game['HOME_TEAM_ID']
                        # Need to get abbr from somewhere, Scoreboard gives IDs.
                        # Can fetch team details or just return generic "vs Opponent"
                        # For MVP, let's just return date and generic info if we can't resolve ID quickly.
                        # Actually GameHeader has HOME_TEAM_ID, VISITOR_TEAM_ID.
                        return {
                            'date': date_str,
                            'is_home': is_home, 
                            'game_id': game['GAME_ID']
                        }
    except Exception as e:
        print(f"Error fetching schedule: {e}")
    return None

def render_player_header(player_id, bio):
    col1, col2 = st.columns([1, 3])
    
    with col1:
        url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                st.image(url, width=180)
            else:
                st.image("https://via.placeholder.com/150/0F1520/FFFFFF?text=No+Wait", width=150) # Fallback
        except:
             st.markdown("🏀") # Simple fallback

    with col2:
        st.markdown(f"<h1>{bio.get('DISPLAY_FIRST_LAST', 'Unknown')}</h1>", unsafe_allow_html=True)
        
        # Info Badge
        st.markdown(
            f"""
            <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 10px;">
                <span style="background:#1E293B; padding:5px 10px; border-radius:4px; font-family:monospace;">#{bio.get('JERSEY', '00')}</span>
                <span style="color:#94A3B8; font-weight:bold;">{bio.get('POSITION', 'N/A')}</span>
                <span style="color:#FF7A00; font-weight:bold;">{bio.get('TEAM_NAME', 'Free Agent')} ({bio.get('TEAM_ABBREVIATION', '')})</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Bio Stats
        st.markdown(
            f"""
            <div style="font-family:monospace; color:#64748B; font-size:0.9rem;">
                HT: {bio.get('HEIGHT', '-')} | WT: {bio.get('WEIGHT', '-')} | EXP: {bio.get('SEASON_EXP', 'R')} YRS<br>
                DRAFT: {bio.get('DRAFT_YEAR', '-')} (R{bio.get('DRAFT_ROUND', '-')} P{bio.get('DRAFT_NUMBER', '-')}) | {bio.get('COUNTRY', 'USA')}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Next Game
        team_id = bio.get('TEAM_ID')
        if team_id:
            next_game = get_next_game(team_id)
            if next_game:
                loc = "vs" if next_game['is_home'] else "@"
                st.info(f"📅 Next Game: {next_game['date']} {loc} Opponent (ID: {next_game.get('game_id')})")
            else:
                st.warning("📅 Next Game: TBD")

def render_metrics(predictions, cis, history_df):
    """
    Renders 2 rows of metric cards.
    """
    row1_cols = st.columns(5)
    row2_cols = st.columns(5)
    
    # Season Avgs for Delta
    season_avgs = history_df[TARGETS].mean()
    
    # Row 1: PTS, REB, AST, STL, BLK
    metrics_r1 = ['PTS', 'REB', 'AST', 'STL', 'BLK']
    for i, m in enumerate(metrics_r1):
        with row1_cols[i]:
            pred = predictions.get(m, 0)
            avg = season_avgs.get(m, 0)
            delta = pred - avg
            ci = cis.get(f'{m}_ci', 0)
            st.metric(label=f"{m} (±{ci})", value=pred, delta=f"{delta:.1f}")

    # Row 2: TOV, FG_PCT, FT_PCT, FG3M, FPTS
    metrics_r2 = ['TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']
    # Format overrides for percentages
    for i, m in enumerate(metrics_r2):
        with row2_cols[i]:
            pred = predictions.get(m, 0)
            avg = season_avgs.get(m, 0)
            delta = pred - avg
            ci = cis.get(f'{m}_ci', 0)
            
            # Formatting
            if 'PCT' in m:
                val_str = f"{pred:.3f}"
                delta_str = f"{delta:.3f}"
            else:
                val_str = f"{pred:.1f}"
                delta_str = f"{delta:.1f}"
                
            st.metric(label=f"{m} (±{ci})", value=val_str, delta=delta_str)

def plot_fantasy_breakdown(predictions):
    """
    Horizontal bar chart of FPTS contributors.
    """
    # DK scoring weights
    weights = {'PTS':1, 'REB':1.25, 'AST':1.5, 'STL':2, 'BLK':2, 'TOV':-0.5, 'FG3M':0} # 3PM bonus is separate logic in loader
    
    data = []
    for k, w in weights.items():
        val = predictions.get(k, 0) * w
        data.append({'Stat': k, 'Fantasy Points': val})
        
    df_plot = pd.DataFrame(data)
    fig = px.bar(df_plot, x='Fantasy Points', y='Stat', orientation='h', 
                 title="Projected Fantasy Breakdown", text_auto='.1f',
                 color='Fantasy Points', color_continuous_scale='Oranges')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0')
    st.plotly_chart(fig, use_container_width=True)

def plot_trends(history_df, predictions, cis):
    """
    Tabbed trend charts.
    """
    tabs = st.tabs(["Points", "Rebounds", "Assists", "Steals", "Fantasy Pts"])
    
    # Helper to plot
    def plot_metric(metric, tab):
        with tab:
            # history (last 20)
            hist = history_df.sort_values(by='GAME_DATE').tail(20)
            
            dates = hist['GAME_DATE'].dt.strftime('%m/%d').tolist()
            vals = hist[metric].tolist()
            
            # Prediction
            pred_val = predictions.get(metric, 0)
            dates.append("NEXT")
            vals.append(pred_val)
            
            # CI
            ci = cis.get(f'{metric}_ci', 0)
            upper = pred_val + ci
            lower = pred_val - ci
            
            fig = go.Figure()
            
            # Main Line
            fig.add_trace(go.Scatter(x=dates, y=vals, mode='lines+markers', name=metric,
                                     line=dict(color='#FF7A00', width=3)))
            
            # Prediction Highlight
            fig.add_trace(go.Scatter(x=[dates[-1]], y=[pred_val], mode='markers', name='Prediction',
                                     marker=dict(size=12, color='#FFFFFF', line=dict(color='#FF7A00', width=2))))
            
            # CI Band (Error Bar on last point)
            fig.add_trace(go.Scatter(
                x=[dates[-1], dates[-1]], 
                y=[lower, upper],
                mode='lines', 
                line=dict(color='rgba(255,255,255,0.5)', width=4),
                name='Confidence'
            ))

            fig.update_layout(
                title=f"{metric} Trend (Last 20 Games)",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#E2E8F0',
                height=350,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#1E293B')
            )
            st.plotly_chart(fig, use_container_width=True)

    plot_metric('PTS', tabs[0])
    plot_metric('REB', tabs[1])
    plot_metric('AST', tabs[2])
    plot_metric('STL', tabs[3])
    plot_metric('FPTS', tabs[4])

def render_season_stats(history_df):
    st.subheader("Season Log (Last 20 Games)")
    
    # Conditional Formatting
    def highlight_above_avg(s):
        is_above = s > s.mean()
        return ['color: #10B981' if v else 'color: #EF4444' for v in is_above]

    # Show last 20
    display_df = history_df.head(20)[['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'FPTS']]
    
    st.dataframe(
        display_df.style.apply(highlight_above_avg, subset=['PTS', 'REB', 'AST', 'FPTS']),
        use_container_width=True
    )

def render_explainability(feature_importances, feature_names):
    with st.expander("🔍 Why this prediction? (Model Explainability)"):
        if not feature_importances is None and len(feature_importances) > 0:
            imp_df = pd.DataFrame({'Feature': feature_names, 'Importance': feature_importances})
            imp_df = imp_df.sort_values(by='Importance', ascending=False).head(10)
            
            fig = px.bar(imp_df, x='Importance', y='Feature', orientation='h', title="Top 10 Drivers for Points Prediction")
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0')
            st.plotly_chart(fig)
        else:
            st.info("Feature importance data not available.")

# --- Logic ---

# Sidebar
roster = get_roster_options()
# Default index
try:
    default_idx = roster.index("LeBron James")
except:
    default_idx = 0

selected_player = st.sidebar.selectbox("Select Player", roster, index=default_idx)
manual_search = st.sidebar.text_input("Or Search Manually", "")

if manual_search:
    query = manual_search
else:
    query = selected_player

refresh = st.sidebar.button("🔄 Refresh Data")
if refresh:
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.caption("v2.0.0 | Powered by `nba_api`")

# Main Loading
if query:
    player = find_player(query)
    
    if not player:
        st.error(f"Player '{query}' not found.")
    else:
        player_id = player['id']
        
        # 1. Fetch Bio
        with st.spinner("Scouting player..."):
            bio = get_player_bio(player_id)
        
        if bio:
            render_player_header(player_id, bio)
            
            # 2. Run Prediction Pipeline
            with st.spinner("Crunching numbers (Training Random Forest Models)..."):
                result = predict_next_game(player_id)
            
            if result:
                # Unpack
                preds = result['predictions']
                cis = result['cis']
                hist_df = result['history_df']
                feats_imp = result['feature_importances']
                feat_names = result['feature_names']
                
                st.markdown("---")
                st.subheader("🤖 AI Performance Projection")
                
                render_metrics(preds, cis, hist_df)
                
                col_chart, col_breakdown = st.columns([2, 1])
                with col_chart:
                    plot_trends(hist_df, preds, cis)
                with col_breakdown:
                    plot_fantasy_breakdown(preds)
                
                render_season_stats(hist_df)
                render_explainability(feats_imp, feat_names)
                
            else:
                st.warning(f"Could not generate predictions. Insufficient data for {bio.get('DISPLAY_FIRST_LAST')}.")
        else:
            st.error("Could not fetch player details.")
